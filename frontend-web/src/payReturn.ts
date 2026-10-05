export const PAY_MESSAGE = "leia-paid";
export const PAY_WINDOW = "leia_pay";
const PAY_FEATURES = "popup=yes,width=480,height=780,scrollbars=yes,resizable=yes";

export function robokassaTokenFromLocation(loc: Location = window.location): string {
  const params = new URLSearchParams(loc.search);
  return (params.get("Shp_token") || params.get("shp_token") || "").trim();
}

export function isRobokassaReturn(loc: Location = window.location): boolean {
  const params = new URLSearchParams(loc.search);
  return Boolean(
    params.get("paid") === "1" ||
      params.get("InvId") ||
      params.get("InvID") ||
      params.get("invid") ||
      params.get("OutSum") ||
      params.get("SignatureValue") ||
      params.get("Shp_token") ||
      params.get("shp_token") ||
      params.get("Shp_payment_id") ||
      params.get("shp_payment_id"),
  );
}

export function paidReadingPath(token: string): string {
  return `/r/${encodeURIComponent(token)}?paid=1`;
}

export function pathReadingToken(loc: Location = window.location): string {
  if (!loc.pathname.startsWith("/r/")) return "";
  return decodeURIComponent(loc.pathname.slice(3).split("/")[0] || "").trim();
}

export function storedReadingToken(): string {
  try {
    return (localStorage.getItem("leia_last_reading") || "").trim();
  } catch {
    return "";
  }
}

/** Robokassa «вернуться в магазин» бьёт в /lk. Человека всегда отправляем на оплаченный разбор, вход не нужен. */
export function consumeRobokassaReturn(loc: Location = window.location): "popup" | "redirect" | null {
  if (!isRobokassaReturn(loc)) return null;
  const token = robokassaTokenFromLocation(loc) || pathReadingToken(loc) || storedReadingToken();

  if (window.opener && !window.opener.closed) {
    try {
      window.opener.postMessage({ type: PAY_MESSAGE, token }, loc.origin);
    } catch {
      /* ignore */
    }
    window.close();
    return "popup";
  }

  if (token && pathReadingToken(loc) !== token) {
    loc.replace(paidReadingPath(token));
    return "redirect";
  }

  if (!token && loc.pathname.startsWith("/lk")) {
    loc.replace(`/payment/success${loc.search}`);
    return "redirect";
  }

  return null;
}

export function openPayPlaceholder(): Window | null {
  try {
    return window.open("about:blank", PAY_WINDOW, PAY_FEATURES);
  } catch {
    return null;
  }
}

export function launchRobokassa(
  url: string,
  popup: Window | null,
): { popup: Window | null; iframe: boolean } {
  if (popup && !popup.closed) {
    try {
      popup.location.href = url;
      popup.focus();
      return { popup, iframe: false };
    } catch {
      /* fall through */
    }
  }
  try {
    const opened = window.open(url, PAY_WINDOW, PAY_FEATURES);
    if (opened) {
      opened.focus();
      return { popup: opened, iframe: false };
    }
  } catch {
    /* iframe fallback */
  }
  return { popup: null, iframe: true };
}

export function listenPayResult(onPaid: (token: string) => void): () => void {
  const handler = (event: MessageEvent) => {
    if (event.origin !== window.location.origin) return;
    const data = event.data as { type?: string; token?: string } | null;
    if (!data || data.type !== PAY_MESSAGE) return;
    onPaid(String(data.token || ""));
  };
  window.addEventListener("message", handler);
  return () => window.removeEventListener("message", handler);
}
