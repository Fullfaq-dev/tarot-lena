const GUEST_KEY = "leia_guest";

function newGuestId(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") {
    return c.randomUUID();
  }
  return `g-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function guestId(): string {
  let id = localStorage.getItem(GUEST_KEY);
  if (!id) {
    id = newGuestId();
    localStorage.setItem(GUEST_KEY, id);
  }
  return id;
}

const ATTR_KEY = "leia_attr";
const YM_ID = 110607194;
const ATTR_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "yclid"];

type Attr = { utm: Record<string, string>; metrika_client_id?: string };

function readAttr(): Attr {
  try {
    const raw = localStorage.getItem(ATTR_KEY);
    if (!raw) return { utm: {} };
    const parsed = JSON.parse(raw) as Attr;
    return { utm: parsed.utm || {}, metrika_client_id: parsed.metrika_client_id };
  } catch {
    return { utm: {} };
  }
}

function writeAttr(next: Attr) {
  localStorage.setItem(ATTR_KEY, JSON.stringify(next));
}

export function attribution(): Attr {
  const current = readAttr();
  const params = new URLSearchParams(window.location.search);
  let changed = false;
  for (const key of ATTR_KEYS) {
    const value = params.get(key);
    if (value && !current.utm[key]) {
      current.utm[key] = value;
      changed = true;
    }
  }
  if (changed) writeAttr(current);
  const ym = (window as unknown as { ym?: (id: number, method: string, cb: (id: string) => void) => void }).ym;
  if (!current.metrika_client_id && ym) {
    ym(YM_ID, "getClientID", (clientID) => {
      const fresh = readAttr();
      if (fresh.metrika_client_id || !clientID) return;
      fresh.metrika_client_id = clientID;
      writeAttr(fresh);
    });
  }
  return current;
}

export function utm(): Record<string, string> {
  return attribution().utm;
}

export function track(name: string, extra?: Record<string, string | number>) {
  try {
    const ym = (window as unknown as { ym?: (id: number, a: string, n: string, p?: Record<string, string | number>) => void }).ym;
    ym?.(YM_ID, "reachGoal", name, extra);
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
      credentials: "include",
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

export function oauthStart(provider: "yandex" | "vk", next = "/lk"): string {
  const params = new URLSearchParams({ guest_id: guestId(), next });
  return `/api/web/auth/${provider}?${params.toString()}`;
}
