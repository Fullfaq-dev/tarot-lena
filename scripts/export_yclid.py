#!/usr/bin/env python3
"""Parse docker nginx json logs for yclid clicks (Direct vs bots vs JS sessions)."""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlparse

DAY = os.environ.get("YCLID_DAY", "28/Sep/2026")
OUT_DIR = os.environ.get("YCLID_OUT", "/tmp/yclid-export")

COMBINED = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) HTTP/[^"]+" '
    r'(?P<status>\d+) (?P<size>\S+) "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)
YCLID_RE = re.compile(r"(?:^|[?&])yclid=(\d+)")
BOT_RE = re.compile(
    r"YandexMetrika|yabs01|YaDirectFetcher|YandexUserproxy|YandexBot|"
    r"compatible; Yandex|HeadlessChrome|\bcurl/|\bwget/|python-requests|"
    r"Go-http-client|scanner|spider|crawler",
    re.I,
)
DOC_PATHS = {"", "/", "/taro", "/matrica", "/sovmestimost", "/lk", "/legal"}
SKIP_PREFIX = ("/assets/", "/api/", "/static/", "/panel/", "/admin-api/", "/callbacks/")
SKIP_FILES = (".js", ".css", ".png", ".jpg", ".jpeg", ".ico", ".svg", ".woff", ".woff2", ".map", ".webp")


def docker_log_path() -> str:
    out = subprocess.check_output(
        ["docker", "inspect", "tarot-lena-nginx-1", "--format", "{{.LogPath}}"],
        text=True,
    ).strip()
    if not out:
        raise SystemExit("nginx container log path empty")
    return out


def open_log(path: str):
    try:
        return open(path, encoding="utf-8", errors="replace")
    except PermissionError:
        proc = subprocess.Popen(["sudo", "cat", path], stdout=subprocess.PIPE, text=True)
        assert proc.stdout is not None
        return proc.stdout


def is_document(method: str, raw_path: str) -> bool:
    if method != "GET":
        return False
    path = raw_path.split("?", 1)[0]
    if path in DOC_PATHS or path.startswith("/r/"):
        return True
    if path.startswith(SKIP_PREFIX) or path.lower().endswith(SKIP_FILES):
        return False
    if path in {"/favicon.ico", "/logo.jpg", "/avatar.png", "/apple-touch-icon.png", "/favicon-192.png"}:
        return False
    return False


def campaign_of(url: str) -> str:
    q = parse_qs(urlparse(url if "://" in url else f"http://x{url}").query)
    vals = q.get("utm_campaign") or q.get("utm_source") or []
    return vals[0] if vals else ""


def parse_yclids(text: str) -> list[str]:
    return YCLID_RE.findall(text.replace("\\u0026", "&"))


def parse_line(msg: str) -> dict | None:
    m = COMBINED.search(msg.strip())
    if not m:
        return None
    path = m.group("path")
    ref = m.group("ref")
    in_req = parse_yclids(path)
    in_ref = parse_yclids(ref)
    yclids = in_req or in_ref
    if not yclids:
        return None
    ua = m.group("ua")
    src = path if in_req else ref
    return {
        "ts": m.group("ts"),
        "ip": m.group("ip"),
        "method": m.group("method"),
        "path": path[:500],
        "status": m.group("status"),
        "ref": ref[:500],
        "ua": ua[:300],
        "yclid": in_req[0] if in_req else in_ref[0],
        "in_request": bool(in_req),
        "document": is_document(m.group("method"), path) and bool(in_req),
        "bot": bool(BOT_RE.search(ua)),
        "campaign": campaign_of(src),
        "sessions_hit": m.group("method") == "POST" and path.startswith("/api/web/sessions"),
    }


def db_yclids() -> set[str]:
    sql = r"""
    SELECT DISTINCT utm->>'yclid'
    FROM web_sessions
    WHERE created_at >= TIMESTAMPTZ '2026-09-28 00:00:00+00'
      AND created_at <  TIMESTAMPTZ '2026-09-29 00:00:00+00'
      AND COALESCE(utm->>'yclid','') <> '';
    """
    try:
        out = subprocess.check_output(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.prod.yml",
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "tarot",
                "-d",
                "tarot",
                "-At",
                "-c",
                sql,
            ],
            cwd="/opt/tarot-lena",
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"db query failed: {exc}", file=sys.stderr)
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    log_path = docker_log_path()
    rows: list[dict] = []
    with open_log(log_path) as fh:
        for line in fh:
            if DAY not in line or "yclid=" not in line:
                continue
            msg = line
            if line.startswith("{"):
                try:
                    msg = json.loads(line).get("log") or line
                except json.JSONDecodeError:
                    pass
            parsed = parse_line(msg)
            if parsed:
                rows.append(parsed)

    db_ids = db_yclids()
    unique: dict[str, dict] = {}
    for row in rows:
        yid = row["yclid"]
        slot = unique.setdefault(
            yid,
            {
                "yclid": yid,
                "first_ts": row["ts"],
                "last_ts": row["ts"],
                "ips": set(),
                "campaigns": set(),
                "hits": 0,
                "landings": 0,
                "bots": 0,
                "js_sessions": 0,
                "in_db": yid in db_ids,
                "ua": row["ua"],
            },
        )
        slot["hits"] += 1
        slot["last_ts"] = row["ts"]
        slot["ips"].add(row["ip"])
        if row["campaign"]:
            slot["campaigns"].add(row["campaign"])
        if row["document"]:
            slot["landings"] += 1
        if row["bot"]:
            slot["bots"] += 1
        if row["sessions_hit"]:
            slot["js_sessions"] += 1

    landings = [r for r in rows if r["document"]]
    landing_ids = {r["yclid"] for r in landings}
    bot_landing_ids = {r["yclid"] for r in landings if r["bot"]}
    js_ids = {yid for yid, s in unique.items() if s["js_sessions"]}
    human_landing_ids = landing_ids - bot_landing_ids

    summary = {
        "day_in_log": DAY,
        "all_lines_with_yclid": len(rows),
        "unique_yclid_any": len(unique),
        "landing_gets_with_yclid_in_url": len(landings),
        "unique_yclid_landings": len(landing_ids),
        "unique_yclid_landings_minus_metrika_bots": len(human_landing_ids),
        "unique_yclid_with_js_session_post": len(js_ids),
        "unique_yclid_in_web_sessions_db": len(db_ids),
        "unique_bot_landing_yclid": len(bot_landing_ids),
        "note": (
            "Кабинет Директа считает клики. Nginx unique landing ≈ клики, которые дошли до сайта. "
            "JS session / БД ≈ счётчик реально отработал. Метрика обычно близка к JS, не к кликам Директа."
        ),
    }

    unique_path = os.path.join(OUT_DIR, "yclid-unique-2026-09-28.csv")
    land_path = os.path.join(OUT_DIR, "yclid-landings-2026-09-28.csv")
    with open(unique_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "yclid",
                "first_ts_utc",
                "last_ts_utc",
                "ip_count",
                "ips",
                "landings",
                "all_hits",
                "bot_hits",
                "js_session_posts",
                "in_web_sessions_db",
                "campaigns",
                "sample_ua",
            ]
        )
        for yid, slot in sorted(unique.items(), key=lambda item: item[1]["first_ts"]):
            writer.writerow(
                [
                    yid,
                    slot["first_ts"],
                    slot["last_ts"],
                    len(slot["ips"]),
                    ";".join(sorted(slot["ips"])),
                    slot["landings"],
                    slot["hits"],
                    slot["bots"],
                    slot["js_sessions"],
                    int(slot["in_db"]),
                    ";".join(sorted(slot["campaigns"])),
                    slot["ua"],
                ]
            )

    with open(land_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ts_utc", "yclid", "ip", "status", "path", "campaign", "bot", "ua"])
        for row in landings:
            writer.writerow(
                [
                    row["ts"],
                    row["yclid"],
                    row["ip"],
                    row["status"],
                    row["path"],
                    row["campaign"],
                    int(row["bot"]),
                    row["ua"],
                ]
            )

    print("===YCLID_SUMMARY===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("===YCLID_UNIQUE_CSV===")
    with open(unique_path, encoding="utf-8") as fh:
        print(fh.read())
    print("===YCLID_LANDINGS_CSV===")
    with open(land_path, encoding="utf-8") as fh:
        print(fh.read())
    print("===YCLID_END===")
    print(f"wrote {unique_path} ({os.path.getsize(unique_path)} bytes)")
    print(f"wrote {land_path} ({os.path.getsize(land_path)} bytes)")


if __name__ == "__main__":
    main()
