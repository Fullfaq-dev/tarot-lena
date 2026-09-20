const GUEST_KEY = "leia_guest";

export function guestId(): string {
  let id = localStorage.getItem(GUEST_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(GUEST_KEY, id);
  }
  return id;
}

export function utm(): Record<string, string> {
  const p = new URLSearchParams(window.location.search);
  const out: Record<string, string> = {};
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]) {
    const v = p.get(key);
    if (v) out[key] = v;
  }
  return out;
}

export function track(name: string, extra?: Record<string, string>) {
  try {
    const ym = (window as unknown as { ym?: (id: number, a: string, n: string) => void }).ym;
    ym?.(110607194, "reachGoal", name);
    fetch("/api/web/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, payload: extra || {} }),
    }).catch(() => undefined);
  } catch {
    /* ignore */
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const parsed = JSON.parse(detail);
      detail = parsed.detail || detail;
    } catch {
      /* raw */
    }
    throw new Error(detail || "Ошибка");
  }
  return res.json();
}
