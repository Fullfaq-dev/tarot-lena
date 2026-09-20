import { useEffect, useState } from "react";
import { api, oauthStart } from "./api";

type Reading = {
  token: string;
  product_name?: string;
  card_id: string;
  paid?: boolean;
  mini?: { title?: string; lead?: string };
  paid_text?: string;
};

type Me = {
  user: {
    id: string;
    name?: string;
    email?: string;
    telegram_bound?: boolean;
    telegram_username?: string | null;
  } | null;
  oauth?: { yandex?: boolean; vk?: boolean };
  plan?: string | null;
  vip?: boolean;
  love_plus?: boolean;
  readings?: Reading[];
  packages?: { id: string; title: string; emoji: string; price_rub: number; pitch: string }[];
};

export function Cabinet() {
  const params = new URLSearchParams(window.location.search);
  const [me, setMe] = useState<Me | null>(null);
  const [err, setErr] = useState("");
  const [readingToken, setReadingToken] = useState(params.get("reading") || "");
  const [text, setText] = useState("");
  const [log, setLog] = useState<{ role: string; text: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [paying, setPaying] = useState(false);

  async function reload() {
    const data = await api<Me>("/api/web/me");
    setMe(data);
  }

  useEffect(() => {
    reload().catch((e) => setErr(e instanceof Error ? e.message : "Не открылся кабинет"));
  }, []);

  const oauth = me?.oauth || {};
  const selected = me?.readings?.find((r) => r.token === readingToken);

  async function send() {
    if (!text.trim()) return;
    setBusy(true);
    setErr("");
    const mine = text.trim();
    setText("");
    setLog((rows) => [...rows, { role: "user", text: mine }]);
    try {
      const r = await api<{ reply: string }>("/api/web/chat", {
        method: "POST",
        body: JSON.stringify({ text: mine, reading_token: readingToken || null }),
      });
      setLog((rows) => [...rows, { role: "leia", text: r.reply }]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Чат не ответил");
    } finally {
      setBusy(false);
    }
  }

  async function buy(packageId: string) {
    if (paying) return;
    setErr("");
    setPaying(true);
    try {
      const r = await api<{ payment_url?: string; demo?: boolean }>("/api/web/packages/checkout", {
        method: "POST",
        body: JSON.stringify({ package_id: packageId }),
      });
      if (r.payment_url) {
        window.location.href = r.payment_url;
        return;
      }
      await reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Оплата не прошла");
    } finally {
      setPaying(false);
    }
  }

  async function bindTelegram() {
    setErr("");
    try {
      const r = await api<{ bound?: boolean; url?: string; username?: string | null }>(
        "/api/web/telegram/bind",
        { method: "POST" },
      );
      if (r.bound) {
        await reload();
        return;
      }
      if (r.url) window.open(r.url, "_blank", "noopener");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не открылась ссылка в бота");
    }
  }

  return (
    <div className="site">
      <div className="sparkles" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <div className="shell">
        <header className="topbar">
          <a className="brand" href="/">
            <span className="brand-mark"><img src="/avatar.png" alt="" /></span>
            <span>Лея</span>
          </a>
          <a className="nav-ghost" href="/">На сайт</a>
        </header>

        {!me?.user && (
          <section className="quiz-frame wide">
            <div className="eyebrow">Личный кабинет</div>
            <h2 className="h">Войди, чтобы сохранить разборы и открыть чат</h2>
            <p className="sub">Яндекс или VK. После входа здесь будет история, пакеты как в Telegram и чат с Леей.</p>
            {oauth.yandex ? (
              <a className="btn" href={oauthStart("yandex", window.location.pathname + window.location.search)}>Войти через Яндекс</a>
            ) : (
              <p className="fine">Яндекс OAuth ещё не подключён — нужны YANDEX_OAUTH_CLIENT_ID и SECRET в .env</p>
            )}
            {oauth.vk ? (
              <a className="btn ghost" href={oauthStart("vk", window.location.pathname + window.location.search)}>Войти через VK</a>
            ) : (
              <p className="fine">VK OAuth ещё не подключён — нужны VK_OAUTH_CLIENT_ID и SECRET в .env</p>
            )}
            {err && <p className="err">{err}</p>}
          </section>
        )}

        {me?.user && (
          <div className="lk-grid">
            <aside className="quiz-aside">
              <img src="/avatar.png" alt="" />
              <h3>{me.user.name || "Ты"}</h3>
              <p>{me.user.email || "аккаунт на сайте"}</p>
              <p className="eyebrow">{me.plan || "Без подписки"}</p>
              {me.user.telegram_bound ? (
                <p className="fine">Telegram: @{me.user.telegram_username || "привязан"}</p>
              ) : (
                <>
                  <p className="fine">Бот и сайт пока разные аккаунты. Привяжи Telegram — покупки и чат станут общими.</p>
                  <button className="btn" type="button" onClick={bindTelegram}>
                    Привязать Telegram
                  </button>
                </>
              )}
              <button
                className="btn link"
                type="button"
                onClick={async () => {
                  await api("/api/web/auth/logout", { method: "POST" });
                  window.location.reload();
                }}
              >
                Выйти
              </button>
            </aside>

            <div>
              <section className="quiz-frame wide">
                <div className="eyebrow">Чат</div>
                <h2 className="h">{selected ? selected.mini?.title || selected.product_name : "Свободный чат"}</h2>
                <p className="sub">
                  {selected
                    ? "Спрашивай про этот разбор."
                    : me.vip
                      ? "VIP: можно писать Лее без привязки к раскладу."
                      : "Выбери оплаченный разбор слева от истории — или возьми VIP, чтобы болтать свободно."}
                </p>
                <div className="chat-log">
                  {selected?.paid_text && <div className="chat-bubble leia"><b>Разбор</b><div className="stream">{selected.paid_text}</div></div>}
                  {log.map((row, i) => (
                    <div key={i} className={`chat-bubble ${row.role === "user" ? "me" : "leia"}`}>{row.text}</div>
                  ))}
                </div>
                <div className="chat-compose">
                  <input
                    className="inp"
                    value={text}
                    placeholder="Напиши Лее…"
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && send()}
                  />
                  <button className="btn" type="button" disabled={busy} onClick={send}>
                    {busy ? "…" : "Отправить"}
                  </button>
                </div>
                {err && <p className="err">{err}</p>}
              </section>

              <section className="quiz-frame wide" style={{ marginTop: 18 }}>
                <div className="eyebrow">История</div>
                <h2 className="h">Твои разборы</h2>
                <div className="cards landing-cards">
                  {(me.readings || []).map((r) => (
                    <button
                      key={r.token}
                      className={`c ${readingToken === r.token ? "on" : ""}`}
                      type="button"
                      onClick={() => setReadingToken(r.token)}
                    >
                      <b>{r.mini?.title || r.product_name || r.card_id}</b>
                      <span className="fine">{r.paid ? "открыт" : "мини"}</span>
                    </button>
                  ))}
                  {!me.readings?.length && <p className="sub">Пока пусто — пройди квиз на главной.</p>}
                </div>
              </section>

              <section className="quiz-frame wide" style={{ marginTop: 18 }}>
                <div className="eyebrow">Пакеты как в Telegram</div>
                <h2 className="h">ЛЮБОВЬ+ и VIP на всё</h2>
                <div className="pkg-grid">
                  {(me.packages || []).map((pkg) => (
                    <article key={pkg.id} className="tar">
                      <h4>{pkg.emoji} {pkg.title}</h4>
                      <div className="pr">{pkg.price_rub} ₽</div>
                      <p className="sub">{pkg.pitch.replace(/\*\*/g, "")}</p>
                      <button className="btn gold" type="button" disabled={paying} onClick={() => buy(pkg.id)}>
                        {paying ? "Открываю оплату…" : "Оплатить"}
                      </button>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
