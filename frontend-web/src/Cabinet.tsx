import { useEffect, useRef, useState } from "react";
import { api, oauthStart } from "./api";

type Reading = {
  token: string;
  product_name?: string;
  card_id: string;
  paid?: boolean;
  source?: string;
  created_at?: string;
  mini?: { title?: string; lead?: string };
  paid_text?: string;
  html?: string | null;
};

type QuizCard = { id: string; title: string; icon: string; tab: string };

type Profile = {
  name: string;
  birth_date: string;
  birth_city: string;
  birth_time: string;
};

type ChatRow = { id?: string; role: string; text: string; html?: string | null };

function LeiaText({ text, html }: { text: string; html?: string | null }) {
  if (html) {
    return <div className="md" dangerouslySetInnerHTML={{ __html: html }} />;
  }
  return <>{text}</>;
}

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

function formatWhen(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function tabFromUrl(): Tab {
  const value = new URLSearchParams(window.location.search).get("tab");
  if (value === "chat" || value === "history" || value === "profile") return value;
  return "profile";
}

export function Cabinet() {
  const params = new URLSearchParams(window.location.search);
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>(params.get("reading") ? "history" : tabFromUrl());
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [text, setText] = useState("");
  const [log, setLog] = useState<ChatRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [paying, setPaying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [openReading, setOpenReading] = useState<string>(params.get("reading") || "");
  const [quizCards, setQuizCards] = useState<QuizCard[]>([]);
  const chatEnd = useRef<HTMLDivElement | null>(null);

  async function reload() {
    const data = await api<Me>("/api/web/me");
    setMe(data);
    if (data.profile) setProfile({ ...emptyProfile, ...data.profile });
    if (data.chat) setLog(data.chat);
  }

  useEffect(() => {
    reload().catch((e) => setErr(e instanceof Error ? e.message : "Не открылся кабинет"));
    api<{ cards: QuizCard[] }>("/api/web/cards")
      .then((d) => setQuizCards(d.cards || []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    chatEnd.current?.scrollIntoView({ block: "end" });
  }, [log, busy, tab]);

  const oauth = me?.oauth || {};

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
        body: JSON.stringify({ text: mine }),
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
                  <h2 className="h">Диалог с Леей</h2>
                  <p className="sub">
                    {me.user.telegram_bound
                      ? "Это тот же чат, что в Telegram. Разборы лежат отдельно во вкладке «Разборы»."
                      : me.vip
                        ? "VIP: можно писать свободно. Готовые разборы — во вкладке «Разборы»."
                        : "Привяжи Telegram или возьми VIP, чтобы писать. Готовые разборы — отдельной вкладкой."}
                  </p>
                  <div className="chat-log">
                    {log.map((row, i) => (
                      <div key={row.id || i} className={`chat-bubble ${row.role === "user" ? "me" : "leia"}`}>
                        {row.role === "leia" ? <LeiaText text={row.text} html={row.html} /> : row.text}
                      </div>
                    ))}
                    {busy && (
                      <div className="chat-bubble leia typing" aria-live="polite">
                        <span className="typing-label">Лея пишет</span>
                        <span className="typing-dots"><span /><span /><span /></span>
                      </div>
                    )}
                    {!log.length && !busy && (
                      <p className="chat-empty">Напиши Лее — продолжим диалог. Расклады сюда не подмешиваются.</p>
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
                  <div className="eyebrow">Разборы</div>
                  <h2 className="h">Проведённые разборы</h2>
                  <p className="sub">Дата и ответ Леи. Чат сюда не подмешивается.</p>
                  <div className="lk-new-readings">
                    <a className="btn gold" href="/#quiz">Новый разбор на сайте</a>
                    <div className="cards landing-cards">
                      {quizCards.map((c) => (
                        <a key={c.id} className="c" href={`/?start=${encodeURIComponent(c.id)}`}>
                          <span className="ic">{c.icon}</span>
                          <b>{c.title}</b>
                        </a>
                      ))}
                    </div>
                  </div>
                  <div className="lk-readings">
                    {(me.readings || []).map((r) => {
                      const open = openReading === r.token;
                      return (
                        <article key={r.token} className={`lk-reading ${open ? "on" : ""}`}>
                          <button
                            className="lk-reading-head"
                            type="button"
                            onClick={() => setOpenReading(open ? "" : r.token)}
                          >
                            <span className="fine">{formatWhen(r.created_at) || "без даты"}</span>
                            <b>{r.mini?.title || r.product_name || r.card_id}</b>
                            <span className="fine">
                              {r.source === "telegram" ? "Telegram" : r.paid ? "сайт" : "сайт · мини"}
                            </span>
                          </button>
                          {open && (
                            <div className="lk-reading-body">
                              <LeiaText
                                text={r.paid_text || r.mini?.lead || "Текст разбора не сохранился."}
                                html={r.html}
                              />
                            </div>
                          )}
                        </article>
                      );
                    })}
                    {!me.readings?.length && (
                      <p className="sub">Пока пусто — выбери карточку выше или сделай расклад в боте.</p>
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
