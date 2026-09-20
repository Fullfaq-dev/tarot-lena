import { useEffect, useRef, useState } from "react";
import { api, oauthStart } from "./api";

type Reading = {
  token: string;
  product_name?: string;
  card_id: string;
  paid?: boolean;
  source?: string;
  mini?: { title?: string; lead?: string };
  paid_text?: string;
};

type Profile = {
  name: string;
  birth_date: string;
  birth_city: string;
  birth_time: string;
};

type ChatRow = { id?: string; role: string; text: string };

type Tab = "profile" | "chat" | "history";

type Me = {
  user: {
    id: string;
    name?: string;
    email?: string;
    telegram_bound?: boolean;
    telegram_username?: string | null;
  } | null;
  profile?: Profile;
  oauth?: { yandex?: boolean; vk?: boolean };
  plan?: string | null;
  vip?: boolean;
  love_plus?: boolean;
  readings?: Reading[];
  chat?: ChatRow[];
  packages?: { id: string; title: string; emoji: string; price_rub: number; pitch: string }[];
};

const emptyProfile: Profile = { name: "", birth_date: "", birth_city: "", birth_time: "" };

function tabFromUrl(): Tab {
  const value = new URLSearchParams(window.location.search).get("tab");
  if (value === "chat" || value === "history" || value === "profile") return value;
  return "profile";
}

export function Cabinet() {
  const params = new URLSearchParams(window.location.search);
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>(tabFromUrl());
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [readingToken, setReadingToken] = useState(params.get("reading") || "");
  const [text, setText] = useState("");
  const [log, setLog] = useState<ChatRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [paying, setPaying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const chatEnd = useRef<HTMLDivElement | null>(null);

  async function reload() {
    const data = await api<Me>("/api/web/me");
    setMe(data);
    if (data.profile) setProfile({ ...emptyProfile, ...data.profile });
    if (data.chat) setLog(data.chat);
  }

  useEffect(() => {
    reload().catch((e) => setErr(e instanceof Error ? e.message : "Не открылся кабинет"));
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ block: "end" });
  }, [log, busy, tab]);

  const oauth = me?.oauth || {};
  const selected = me?.readings?.find((r) => r.token === readingToken);

  function goTab(next: Tab) {
    setTab(next);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.replaceState({}, "", url);
  }

  async function send() {
    if (busy || !text.trim()) return;
    setBusy(true);
    setErr("");
    const mine = text.trim();
    setText("");
    setLog((rows) => [...rows, { role: "user", text: mine }]);
    try {
      const r = await api<{ reply: string; chat?: ChatRow[] }>("/api/web/chat", {
        method: "POST",
        body: JSON.stringify({ text: mine, reading_token: readingToken || null }),
      });
      if (r.chat) setLog(r.chat);
      else setLog((rows) => [...rows, { role: "leia", text: r.reply }]);
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

  async function saveProfile() {
    setSaving(true);
    setErr("");
    setOk("");
    try {
      const data = await api<Me>("/api/web/profile", {
        method: "PATCH",
        body: JSON.stringify(profile),
      });
      setMe(data);
      if (data.profile) setProfile({ ...emptyProfile, ...data.profile });
      if (data.chat) setLog(data.chat);
      setOk("Сохранила — в Telegram и на сайте это один профиль.");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не сохранилось");
    } finally {
      setSaving(false);
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
          <nav className="lk-nav">
            <a className="nav-ghost" href="/#quiz">Квиз</a>
            <a className="nav-ghost" href="/">На сайт</a>
          </nav>
        </header>

        {!me?.user && (
          <section className="quiz-frame lk-login">
            <div className="eyebrow">Личный кабинет</div>
            <h2 className="h">Войди, чтобы сохранить разборы и открыть чат</h2>
            <p className="sub">Яндекс или VK. ФИО и дата рождения подтянутся в профиль, если их отдал провайдер.</p>
            {oauth.yandex ? (
              <a className="btn" href={oauthStart("yandex", window.location.pathname + window.location.search)}>Войти через Яндекс</a>
            ) : (
              <p className="fine">Яндекс OAuth ещё не подключён</p>
            )}
            {oauth.vk ? (
              <a className="btn ghost" href={oauthStart("vk", window.location.pathname + window.location.search)}>Войти через VK</a>
            ) : (
              <p className="fine">VK OAuth ещё не подключён</p>
            )}
            <a className="btn gold" href="/#quiz">Сначала пройти квиз</a>
            {err && <p className="err">{err}</p>}
          </section>
        )}

        {me?.user && (
          <div className="lk-grid">
            <aside className="lk-aside">
              <img src="/avatar.png" alt="" />
              <h3>{profile.name || me.user.name || "Ты"}</h3>
              <p>{me.user.email || "аккаунт на сайте"}</p>
              <p className="eyebrow">{me.plan || "Без подписки"}</p>
              {me.user.telegram_bound ? (
                <p className="fine">Telegram: @{me.user.telegram_username || "привязан"}</p>
              ) : (
                <>
                  <p className="fine">Бот и сайт пока разные аккаунты. Привяжи Telegram — профиль, чат и разборы станут общими.</p>
                  <button className="btn" type="button" onClick={bindTelegram}>
                    Привязать Telegram
                  </button>
                </>
              )}
              <a className="btn gold" href="/#quiz">Новый разбор</a>
              <div className="lk-tabs">
                <button className={tab === "profile" ? "on" : ""} type="button" onClick={() => goTab("profile")}>Профиль</button>
                <button className={tab === "chat" ? "on" : ""} type="button" onClick={() => goTab("chat")}>Чат</button>
                <button className={tab === "history" ? "on" : ""} type="button" onClick={() => goTab("history")}>Разборы</button>
              </div>
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

            <div className="lk-main">
              {tab === "profile" && (
                <>
                  <section className="quiz-frame wide">
                    <div className="eyebrow">Личное</div>
                    <h2 className="h">Профиль</h2>
                    <p className="sub">Эти данные видит Лея в Telegram и на сайте.</p>
                    <div className="lk-fields lk-fields-wide">
                      <div className="field">
                        <label>Имя</label>
                        <input className="inp" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
                      </div>
                      <div className="field">
                        <label>Дата рождения</label>
                        <input className="inp" placeholder="дд.мм.гггг" value={profile.birth_date} onChange={(e) => setProfile({ ...profile, birth_date: e.target.value })} />
                      </div>
                      <div className="field">
                        <label>Место рождения</label>
                        <input className="inp" placeholder="город" value={profile.birth_city} onChange={(e) => setProfile({ ...profile, birth_city: e.target.value })} />
                      </div>
                      <div className="field">
                        <label>Время рождения</label>
                        <input className="inp" placeholder="если знаешь" value={profile.birth_time} onChange={(e) => setProfile({ ...profile, birth_time: e.target.value })} />
                      </div>
                      <button className="btn ghost" type="button" disabled={saving} onClick={saveProfile}>
                        {saving ? "Сохраняю…" : "Сохранить профиль"}
                      </button>
                    </div>
                    {ok && <p className="ok">{ok}</p>}
                    {err && <p className="err">{err}</p>}
                  </section>

                  <section className="quiz-frame wide" style={{ marginTop: 18 }}>
                    <div className="eyebrow">Оплата</div>
                    <h2 className="h">Пакеты как в Telegram</h2>
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
                </>
              )}

              {tab === "chat" && (
                <section className="quiz-frame wide">
                  <div className="eyebrow">Чат</div>
                  <h2 className="h">{selected ? selected.mini?.title || selected.product_name : "Диалог с Леей"}</h2>
                  <p className="sub">
                    {me.user.telegram_bound
                      ? "Это тот же чат, что в Telegram: история и память общие."
                      : me.vip
                        ? "VIP: можно писать без привязки к раскладу."
                        : "Выбери оплаченный разбор во вкладке «Разборы» — или привяжи Telegram."}
                  </p>
                  {selected && (
                    <p className="fine" style={{ textAlign: "left", marginBottom: 8 }}>
                      В контексте: {selected.mini?.title || selected.product_name}
                      {" · "}
                      <button type="button" className="nav-ghost" onClick={() => setReadingToken("")}>сбросить</button>
                    </p>
                  )}
                  <div className="chat-log">
                    {log.map((row, i) => (
                      <div key={row.id || i} className={`chat-bubble ${row.role === "user" ? "me" : "leia"}`}>{row.text}</div>
                    ))}
                    {busy && (
                      <div className="chat-bubble leia typing" aria-live="polite">
                        <span className="typing-label">Лея пишет</span>
                        <span className="typing-dots"><span /><span /><span /></span>
                      </div>
                    )}
                    {!log.length && !busy && (
                      <p className="chat-empty">Напиши Лее — продолжим с того места, где остановились в Telegram.</p>
                    )}
                    <div ref={chatEnd} />
                  </div>
                  <div className="chat-compose">
                    <input
                      className="inp"
                      value={text}
                      disabled={busy}
                      placeholder={busy ? "Лея ещё отвечает…" : "Напиши Лее…"}
                      onChange={(e) => setText(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && !busy && send()}
                    />
                    <button className="btn" type="button" disabled={busy || !text.trim()} onClick={send}>
                      {busy ? "Пишет…" : "Отправить"}
                    </button>
                  </div>
                  {err && <p className="err">{err}</p>}
                </section>
              )}

              {tab === "history" && (
                <section className="quiz-frame wide">
                  <div className="eyebrow">История</div>
                  <h2 className="h">Твои разборы</h2>
                  <p className="sub">С сайта и из Telegram — один список, если аккаунты привязаны.</p>
                  <div className="cards landing-cards">
                    {(me.readings || []).map((r) => (
                      <button
                        key={r.token}
                        className={`c ${readingToken === r.token ? "on" : ""}`}
                        type="button"
                        onClick={() => {
                          setReadingToken(r.token);
                          goTab("chat");
                        }}
                      >
                        <b>{r.mini?.title || r.product_name || r.card_id}</b>
                        <span className="fine">
                          {r.source === "telegram" ? "telegram" : r.paid ? "сайт · открыт" : "сайт · мини"}
                          {r.mini?.lead ? ` · ${r.mini.lead}` : ""}
                        </span>
                      </button>
                    ))}
                    {!me.readings?.length && (
                      <p className="sub">Пока пусто — <a href="/#quiz">пройди квиз</a> или сделай расклад в боте.</p>
                    )}
                  </div>
                </section>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
