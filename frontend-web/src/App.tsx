import { useEffect, useMemo, useRef, useState } from "react";
import { api, attribution, guestId, oauthStart, pingSession, track } from "./api";
import { Cabinet, LeiaText, TelegramLogin } from "./Cabinet";
import { Landing, type LandingPage } from "./Landing";
import { CookieBanner, ConsentBoxes, SiteFooter } from "./legal";
import {
  isRobokassaReturn,
  launchRobokassa,
  listenPayResult,
  openPayPlaceholder,
} from "./payReturn";
import { maskTime, TIME_PLACEHOLDER } from "./timeMask";

type Card = {
  id: string;
  tab: string;
  title: string;
  icon: string;
  branch: string;
  cards_n: number;
  product_name: string;
  questions: { text: string; options: string[] }[];
  positions: string[];
  open_blocks: string[];
  closed_blocks: string[];
  free: boolean;
  fallback_question?: string;
};

type MiniBlock = {
  title: string;
  text: string;
  image?: string;
  name?: string;
  closed?: boolean;
};

type MiniStats = {
  percent?: number;
  life_paths?: string;
  signs?: string;
  elements?: string;
  life_path?: string | number;
  year_arcana?: string;
  chart?: Record<string, number>;
};

type Offer = {
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  cta?: string;
  gift?: string;
  algorithm?: string;
  price_caption?: string;
  question_example?: string;
  price_rub?: number;
  strike_rub?: number;
  show_strike?: boolean;
  fine?: string;
};

type Mini = {
  source?: string;
  pending?: boolean;
  verdict?: string;
  body?: string[];
  hook?: string;
  paywall_title?: string;
  paywall_bullets?: string[];
  question_example?: string;
  tg_question_example?: string;
  mirror: string;
  blocks: MiniBlock[];
  stats?: MiniStats;
  cut: string;
  fade: boolean;
  cta: string;
  lead: string;
  title: string;
  free: boolean;
};

type Reading = {
  token: string;
  card_id: string;
  branch: string;
  status: string;
  mini: Mini;
  price_rub: number;
  product_name: string;
  drawn: { name?: string; image?: string }[];
  paid?: boolean;
  awaiting_pay?: boolean;
  paid_text?: string;
  paid_html?: string | null;
  includes?: string[];
  context?: string;
  offer?: Offer;
  generating?: boolean;
  question_budget?: number;
};

function fromRobokassaReturn() {
  return isRobokassaReturn();
}

function awaitingKey(token: string) {
  return `leia_awaiting_${token}`;
}

function rememberReading(token: string) {
  try {
    localStorage.setItem("leia_last_reading", token);
  } catch {
    /* ignore */
  }
  try {
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `leia_last_reading=${encodeURIComponent(token)}; Path=/; Max-Age=2592000; SameSite=Lax${secure}`;
  } catch {
    /* ignore */
  }
}

function formatRub(n: number) {
  return Math.round(n).toLocaleString("ru-RU");
}

function shouldWaitForPaid(token: string, reading: Reading) {
  if (fromRobokassaReturn()) return true;
  if (sessionStorage.getItem(awaitingKey(token)) === "1") return true;
  if (reading.awaiting_pay || reading.generating) return true;
  const ref = document.referrer || "";
  return /robokassa|auth\.robokassa|\/payment\/success/i.test(ref);
}

function readingTrack(reading: Reading) {
  return {
    product_name: reading.product_name || "",
    price_rub: reading.price_rub || 0,
    branch: reading.branch || "",
    card_id: reading.card_id || "",
  };
}

function miniParagraphs(mini: Mini): string[] {
  const parts = [mini.verdict, ...(mini.body || []), mini.hook].map((item) => (item || "").trim()).filter(Boolean);
  if (parts.length) return parts;
  const fallback = [mini.mirror, mini.lead].map((item) => (item || "").trim()).filter(Boolean);
  return fallback;
}

function mark(text: string) {
  return text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
}

function MatrixChart({ chart }: { chart: Record<string, number> }) {
  const pts: { key: string; x: number; y: number }[] = [
    { key: "top", x: 50, y: 10 },
    { key: "tr", x: 78, y: 22 },
    { key: "right", x: 90, y: 50 },
    { key: "br", x: 78, y: 78 },
    { key: "bottom", x: 50, y: 90 },
    { key: "bl", x: 22, y: 78 },
    { key: "left", x: 10, y: 50 },
    { key: "tl", x: 22, y: 22 },
    { key: "center", x: 50, y: 50 },
  ];
  return (
    <svg className="matrix-svg" viewBox="0 0 100 100" aria-hidden="true">
      <rect x="18" y="18" width="64" height="64" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <rect x="32" y="32" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.2" transform="rotate(45 50 50)" />
      {pts.map((p) => (
        <g key={p.key}>
          <circle cx={p.x} cy={p.y} r={p.key === "center" ? 8 : 6.2} className={p.key === "center" ? "on" : undefined} />
          <text x={p.x} y={p.y + 1.2} textAnchor="middle" dominantBaseline="middle">{chart[p.key] ?? ""}</text>
        </g>
      ))}
    </svg>
  );
}

function todayMiniKey() {
  const d = new Date();
  return `leia_mini_${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function deviceMiniCount() {
  return Number(localStorage.getItem(todayMiniKey()) || 0);
}

function bumpDeviceMini() {
  localStorage.setItem(todayMiniKey(), String(deviceMiniCount() + 1));
}

function landingPage(): LandingPage {
  const path = window.location.pathname.replace(/\/$/, "") || "/";
  if (path === "/taro") return "taro";
  if (path === "/matrica") return "matrica";
  if (path === "/sovmestimost") return "sovmestimost";
  return "home";
}

function AuthWays({
  next,
  oauth,
  bot,
  onError,
  disabled,
}: {
  next: string;
  oauth: { yandex?: boolean; vk?: boolean; telegram?: boolean };
  bot?: string;
  onError: (message: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className={`pay-auth${disabled ? " dim" : ""}`}>
      {oauth.telegram && bot ? (
        <TelegramLogin label="Войти через Telegram" next={next} onError={onError} disabled={disabled} />
      ) : null}
      {oauth.yandex ? (
        disabled ? (
          <button className="btn ghost" type="button" disabled>Войти через Яндекс</button>
        ) : (
          <a className="btn ghost" href={oauthStart("yandex", next)}>Войти через Яндекс</a>
        )
      ) : null}
      {oauth.vk ? (
        disabled ? (
          <button className="btn ghost" type="button" disabled>Войти через VK</button>
        ) : (
          <a className="btn ghost" href={oauthStart("vk", next)}>Войти через VK</a>
        )
      ) : null}
    </div>
  );
}

export function App() {
  const page = landingPage();
  const tokenFromPath = window.location.pathname.startsWith("/r/")
    ? decodeURIComponent(window.location.pathname.slice(3).split("/")[0] || "")
    : "";
  const [cards, setCards] = useState<Card[]>([]);
  const [cfg, setCfg] = useState({
    bot_username: "astro_leia_bot",
    legal_url: "/legal",
    oauth: { yandex: false, vk: false, telegram: false },
    show_strike_price: true,
    question_price_rub: 99,
    question_pack5_price_rub: 199,
    question_free_limit: 3,
    paywall_gift: "В подарок: 3 уточняющих вопроса к твоему разбору",
    paywall_algorithm_taro: "Карты раскладывает алгоритм, без ручных ошибок. Ответ через минуту",
    paywall_algorithm_date: "Числа считает алгоритм, без ручных ошибок. Ответ через минуту",
    paywall_price_caption_taro: "индивидуальный разбор + 3 вопроса",
    paywall_price_caption_date: "индивидуальный расчёт + 3 вопроса",
  });
  const [tab, setTab] = useState(page === "home" ? "rel" : "rel");
  const [screen, setScreen] = useState(tokenFromPath ? 5 : 1);
  const [sel, setSel] = useState<Card | null>(null);
  const [qi, setQi] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [deck, setDeck] = useState<{ slug: string; image?: string }[]>([]);
  const [picks, setPicks] = useState<string[]>([]);
  const [birth, setBirth] = useState("");
  const [city, setCity] = useState("");
  const [time, setTime] = useState("");
  const [partner, setPartner] = useState("");
  const [email, setEmail] = useState("");
  const [reading, setReading] = useState<Reading | null>(null);
  const [tariff, setTariff] = useState<"base" | "bundle">("base");
  const [err, setErr] = useState("");
  const [vpn, setVpn] = useState(false);
  const [mkt, setMkt] = useState(false);
  const [priv, setPriv] = useState(false);
  const [recur, setRecur] = useState(false);
  const [stream, setStream] = useState("");
  const [paying, setPaying] = useState(false);
  const [waitingPay, setWaitingPay] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const [payLive, setPayLive] = useState(false);
  const [payFrame, setPayFrame] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [askText, setAskText] = useState("");
  const [askLog, setAskLog] = useState<{ role: string; text: string; html?: string | null }[]>([]);
  const [askLeft, setAskLeft] = useState<number | null>(null);
  const [asking, setAsking] = useState(false);
  const [needPack, setNeedPack] = useState(false);
  const [exitFrom, setExitFrom] = useState<"mini" | "paywall">("mini");
  const payPopup = useRef<Window | null>(null);
  const payKind = useRef<"reading" | "questions">("reading");
  const budgetBefore = useRef(0);
  const payUrlRef = useRef("");

  const showLanding = screen === 1 && !tokenFromPath;

  useEffect(() => {
    api<{ cards: Card[] }>("/api/web/cards").then(async (d) => {
      setCards(d.cards);
      const startId = new URLSearchParams(window.location.search).get("start");
      if (!startId || tokenFromPath) return;
      const card = d.cards.find((item) => item.id === startId);
      if (!card) return;
      setSel(card);
      setQi(0);
      setAnswers(Array(card.questions.length).fill(""));
      setPicks([]);
      if (card.branch === "taro") {
        const deckData = await api<{ cards: { slug: string; image?: string }[] }>("/api/web/deck?n=7");
        setDeck(deckData.cards);
      }
      setScreen(2);
    });
    api<typeof cfg>("/api/web/config").then((d) =>
      setCfg((prev) => ({ ...prev, ...d, oauth: { ...prev.oauth, ...(d.oauth || {}) } })),
    );
    pingSession();
    [500, 2000, 5000].forEach((ms) => window.setTimeout(() => pingSession(), ms));
    api<{ profile?: { birth_date?: string; birth_city?: string; birth_time?: string }; user?: { email?: string } | null }>(
      "/api/web/me",
    )
      .then((d) => {
        setLoggedIn(Boolean(d.user));
        if (d.user?.email) setEmail((v) => v || d.user?.email || "");
        const p = d.profile;
        if (!p) return;
        if (p.birth_date) setBirth((v) => v || p.birth_date || "");
        if (p.birth_city) setCity((v) => v || p.birth_city || "");
        if (p.birth_time) setTime((v) => v || p.birth_time || "");
      })
      .catch(() => undefined);
    if (tokenFromPath) {
      api<Reading>(`/api/web/readings/${tokenFromPath}`)
        .then((r) => {
          setReading(r);
          rememberReading(r.token);
          const params = new URLSearchParams(window.location.search);
          if (params.get("pay") === "fail") {
            setErr("Оплата не прошла. Разбор на месте — можно оплатить ещё раз.");
            setScreen(7);
            return;
          }
          if (r.paid) {
            sessionStorage.removeItem(awaitingKey(tokenFromPath));
            window.history.replaceState({}, "", `/r/${tokenFromPath}`);
            setScreen(8);
            return;
          }
          if (r.generating || shouldWaitForPaid(tokenFromPath, r)) {
            setWaitingPay(true);
            setScreen(5);
            return;
          }
          if (params.get("pay") === "1") {
            setScreen(7);
            return;
          }
          setScreen(6);
        })
        .catch(() => setErr("Ссылка не найдена или истекла"));
    }
  }, [tokenFromPath]);

  useEffect(() => {
    const waitToken = reading?.token || tokenFromPath;
    if (!waitingPay || !waitToken) return;
    let cancelled = false;
    let attempts = 0;
    let timer = 0;
    const closePayUi = () => {
      sessionStorage.removeItem(awaitingKey(waitToken));
      setWaitingPay(false);
      setPayLive(false);
      setPayOpen(false);
      setPayFrame("");
      setPaying(false);
      try {
        payPopup.current?.close();
      } catch {
        /* ignore */
      }
      payPopup.current = null;
    };
    const finishPaid = (r: Reading) => {
      closePayUi();
      window.history.replaceState({}, "", `/r/${waitToken}`);
      setScreen(8);
      setReading(r);
    };
    const tick = () => {
      api<Reading>(`/api/web/readings/${waitToken}`)
        .then((r) => {
          if (cancelled) return;
          setReading(r);
          if (payKind.current === "questions") {
            const grew = typeof r.question_budget === "number" && r.question_budget > budgetBefore.current;
            if (grew || attempts >= 6) {
              closePayUi();
              setNeedPack(false);
              payKind.current = "reading";
              api<{ chat_left?: number; question_budget?: number; chat?: { role: string; text: string; html?: string | null }[] }>(
                `/api/web/readings/${waitToken}/chat`,
              )
                .then((d) => {
                  if (typeof d.chat_left === "number") setAskLeft(d.chat_left);
                  if (d.chat?.length) setAskLog(d.chat.map((row) => ({ role: row.role, text: row.text, html: row.html })));
                })
                .catch(() => undefined);
              return;
            }
          } else if (r.paid) {
            finishPaid(r);
            return;
          }
          attempts += 1;
          if (attempts >= 80) {
            setWaitingPay(false);
            setPayLive(false);
            setErr("Оплата ещё подтверждается. Обнови страницу — полный разбор откроется по этой ссылке, вход не нужен.");
            setScreen(7);
            return;
          }
          timer = window.setTimeout(tick, 1500);
        })
        .catch(() => {
          if (cancelled) return;
          attempts += 1;
          if (attempts >= 80) {
            setWaitingPay(false);
            setPayLive(false);
            setErr("Не получилось открыть разбор. Обнови страницу — ссылка та же, логин не нужен.");
            return;
          }
          timer = window.setTimeout(tick, 1500);
        });
    };
    tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [waitingPay, reading?.token, tokenFromPath]);

  useEffect(() => {
    return listenPayResult((token) => {
      const current = token || reading?.token || tokenFromPath;
      if (!current) return;
      rememberReading(current);
      sessionStorage.setItem(awaitingKey(current), "1");
      setWaitingPay(true);
    });
  }, [reading?.token, tokenFromPath]);

  useEffect(() => {
    if (screen !== 8 || !reading?.token) return;
    api<{ chat?: { role: string; text: string; html?: string | null }[]; chat_left?: number; question_budget?: number }>(
      `/api/web/readings/${reading.token}/chat`,
    )
      .then((d) => {
        if (d.chat?.length) setAskLog(d.chat.map((row) => ({ role: row.role, text: row.text, html: row.html })));
        if (typeof d.chat_left === "number") setAskLeft(d.chat_left);
        if (typeof d.question_budget === "number") setNeedPack(d.chat_left === 0);
      })
      .catch(() => undefined);
  }, [screen, reading?.token]);

  useEffect(() => {
    if (screen === 7 && reading) {
      track("paywall_view", {
        ...readingTrack(reading),
        strike_price: reading.offer?.show_strike ? reading.offer.strike_rub || 0 : 0,
      });
    }
    if (screen === 8 && reading?.paid) {
      const key = `leia_purchase_${reading.token}`;
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, "1");
        track("purchase", { order_price: reading.price_rub, currency: "RUB" });
      }
    }
  }, [screen, reading]);

  useEffect(() => {
    if (screen !== 8 || !reading?.paid_text || reading.paid_html) {
      return undefined;
    }
    let i = 0;
    const text = reading.paid_text;
    const id = window.setInterval(() => {
      i += 4;
      setStream(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, 16);
    return () => window.clearInterval(id);
  }, [screen, reading?.paid_text, reading?.paid_html]);

  useEffect(() => {
    if (!reading) return;
    setAskLeft(reading.question_budget ?? cfg.question_free_limit);
    setNeedPack(false);
  }, [reading?.token, reading?.question_budget, cfg.question_free_limit]);

  useEffect(() => {
    setAskLog([]);
    setAskText("");
  }, [reading?.token]);

  const q = sel?.questions[qi];
  const visible = useMemo(() => {
    if (page === "taro") return cards.filter((c) => c.tab === "rel" && c.branch === "taro");
    if (page === "matrica") return cards.filter((c) => c.branch === "date");
    if (page === "sovmestimost") return cards.filter((c) => c.branch === "pair");
    return cards.filter((c) => c.tab === tab);
  }, [cards, tab, page]);

  function goHome() {
    setScreen(1);
    setSel(null);
    setReading(null);
    setErr("");
    setWaitingPay(false);
    setPayOpen(false);
    window.history.replaceState({}, "", page === "home" ? "/" : `/${page}`);
  }

  async function pickCard(card: Card) {
    setSel(card);
    setQi(0);
    setAnswers(Array(card.questions.length).fill(""));
    setPicks([]);
    track("kart_click");
    track(`kart_click_${card.id}`);
    track("quiz_start");
    if (card.branch === "taro") {
      const d = await api<{ cards: { slug: string; image?: string }[] }>("/api/web/deck?n=7");
      setDeck(d.cards);
    }
    setScreen(2);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function chooseOpt(opt: string) {
    const next = [...answers];
    next[qi] = opt;
    setAnswers(next);
  }

  function quizNext() {
    if (!sel) return;
    if (!answers[qi]) return;
    if (qi < sel.questions.length - 1) {
      setQi(qi + 1);
      return;
    }
    track("quiz_complete");
    setScreen(sel.branch === "taro" ? 3 : 4);
  }

  function togglePick(slug: string) {
    if (!sel) return;
    if (picks.includes(slug)) return;
    if (picks.length >= sel.cards_n) return;
    setPicks([...picks, slug]);
    track("cards_picked");
  }

  async function calculate() {
    if (!sel) return;
    if (deviceMiniCount() >= 5) {
      track("mini_limit");
      setScreen(14);
      return;
    }
    setErr("");
    setScreen(5);
    const started = Date.now();
    try {
      const r = await api<Reading>("/api/web/readings", {
        method: "POST",
        body: JSON.stringify({
          guest_id: guestId(),
          card_id: sel.id,
          answers,
          slugs: picks,
          birth,
          birth_city: city,
          birth_time: time,
          partner_birth: partner,
          utm: attribution().utm,
          metrika_client_id: attribution().metrika_client_id,
          quiz_done: true,
        }),
      });
      bumpDeviceMini();
      setReading(r);
      rememberReading(r.token);
      window.history.replaceState({}, "", `/r/${r.token}`);
      track("calc_done", readingTrack(r));
      const wait = 1600 - (Date.now() - started);
      if (wait > 0) await new Promise((res) => setTimeout(res, wait));
      setScreen(6);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Не получилось";
      if (/закончились/i.test(msg)) {
        track("mini_limit");
        setScreen(14);
        return;
      }
      setErr(msg);
      setScreen(4);
    }
  }

  async function retryMini() {
    if (!reading) return;
    setErr("");
    setScreen(5);
    try {
      const r = await api<Reading>(`/api/web/readings/${reading.token}/retry-mini`, { method: "POST" });
      setReading(r);
      setScreen(6);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не получилось дописать разбор");
      setScreen(6);
    }
  }

  function goTelegramExit(from: "mini" | "paywall") {
    setExitFrom(from);
    if (reading) track("exit_click", { card_id: reading.card_id, from });
    setScreen(13);
  }

  async function askLeia() {
    if (!reading || !askText.trim() || asking || paying) return;
    const mine = askText.trim();
    setAskText("");
    setErr("");
    setAskLog((rows) => [...rows, { role: "user", text: mine }]);
    setAsking(true);
    try {
      const r = await api<{
        reply?: string;
        chat?: { role: string; text: string; html?: string | null }[];
        chat_left?: number;
        need_pack?: boolean;
      }>(`/api/web/readings/${reading.token}/ask`, {
        method: "POST",
        body: JSON.stringify({ text: mine, guest_id: guestId() }),
      });
      if (r.need_pack) {
        setNeedPack(true);
        setAskLeft(0);
        if (r.chat) setAskLog(r.chat.map((row) => ({ role: row.role, text: row.text, html: row.html })));
        return;
      }
      track("question_free", { card_id: reading.card_id, n: (reading.question_budget || 3) - (r.chat_left || 0) });
      if (r.chat) setAskLog(r.chat.map((row) => ({ role: row.role, text: row.text, html: row.html })));
      else if (r.reply) setAskLog((rows) => [...rows, { role: "leia", text: r.reply || "" }]);
      if (typeof r.chat_left === "number") {
        setAskLeft(r.chat_left);
        if (r.chat_left <= 0) setNeedPack(true);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Лея сейчас не отвечает. Напиши ещё раз.");
    } finally {
      setAsking(false);
    }
  }

  async function startRobokassa(url: string, token: string, kind: "reading" | "questions" = "reading") {
    payKind.current = kind;
    budgetBefore.current = reading?.question_budget || cfg.question_free_limit;
    payUrlRef.current = url;
    sessionStorage.setItem(awaitingKey(token), "1");
    rememberReading(token);
    const launched = launchRobokassa(url, payPopup.current);
    payPopup.current = launched.popup;
    setPayFrame(launched.iframe ? url : "");
    setPayOpen(true);
    setPayLive(true);
    setWaitingPay(true);
    window.history.replaceState({}, "", `/r/${token}`);
  }

  async function buyQuestions(pack: "q1" | "q5") {
    if (!reading || paying) return;
    const popup = openPayPlaceholder();
    payPopup.current = popup;
    setPaying(true);
    try {
      const r = await api<{ payment_url?: string; token: string }>(
        `/api/web/readings/${reading.token}/checkout`,
        { method: "POST", body: JSON.stringify({ tariff: pack, privacy: true }) },
      );
      track("question_paid", { card_id: reading.card_id, pack: pack === "q5" ? 5 : 1 });
      if (r.payment_url) {
        await startRobokassa(r.payment_url, r.token || reading.token, "questions");
        return;
      }
      popup?.close();
    } catch (e) {
      popup?.close();
      setErr(e instanceof Error ? e.message : "Не получилось");
    } finally {
      setPaying(false);
    }
  }

  function openPay(next: "base" | "bundle" = "base") {
    setTariff(next);
    setErr("");
    setPayOpen(true);
  }

  async function pay() {
    if (!reading || paying) return;
    const mail = email.trim();
    if (!priv) {
      setErr("Нужно согласие на обработку персональных данных и оферту");
      return;
    }
    if (mail && !mail.includes("@")) {
      setErr("Похоже, в почте опечатка");
      return;
    }
    setErr("");
    const popup = openPayPlaceholder();
    payPopup.current = popup;
    setPaying(true);
    track("checkout_start", readingTrack(reading));
    try {
      const r = await api<{ payment_url?: string; demo?: boolean; token: string }>(
        `/api/web/readings/${reading.token}/checkout`,
        {
          method: "POST",
          body: JSON.stringify({
            tariff,
            email: mail || undefined,
            marketing: mkt,
            privacy: priv,
          }),
        },
      );
      if (r.payment_url) {
        await startRobokassa(r.payment_url, r.token || reading.token);
        return;
      }
      popup?.close();
      const full = await api<Reading>(`/api/web/readings/${r.token}`);
      setReading(full);
      window.history.replaceState({}, "", `/r/${r.token}`);
      if (full.paid) {
        sessionStorage.removeItem(awaitingKey(r.token));
        setPayOpen(false);
        setPayLive(false);
        setScreen(8);
      } else {
        sessionStorage.setItem(awaitingKey(r.token), "1");
        setWaitingPay(true);
        setScreen(5);
      }
    } catch (e) {
      popup?.close();
      setErr(e instanceof Error ? e.message : "Оплата не прошла");
    } finally {
      setPaying(false);
    }
  }

  async function buy(kind: "upsell" | "unlimited") {
    if (!reading || paying) return;
    if (kind === "unlimited" && !email.trim()) {
      setErr("Нужна почта — на неё придёт напоминание за сутки до списания");
      return;
    }
    if (kind === "unlimited" && !priv) {
      setErr("Нужно согласие на обработку персональных данных и оферту");
      return;
    }
    if (kind === "unlimited" && !recur) {
      setErr("Нужна галочка согласия на подписку");
      return;
    }
    setPaying(true);
    try {
      const r = await api<{ payment_url?: string; token: string }>(
        `/api/web/readings/${reading.token}/checkout`,
        {
          method: "POST",
          body: JSON.stringify({
            tariff: kind,
            recur_consent: recur,
            email: email.trim() || undefined,
            marketing: mkt,
            privacy: priv,
          }),
        },
      );
      if (r.payment_url) {
        sessionStorage.setItem(awaitingKey(reading.token), "1");
        window.location.href = r.payment_url;
        return;
      }
      if (kind === "unlimited") track("subscribe");
      else track("upsell_purchase");
      setScreen(kind === "upsell" ? 10 : 11);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не получилось");
    } finally {
      setPaying(false);
    }
  }

  const price = reading?.price_rub || 590;
  const payAmount = price;
  const offer = reading?.offer;
  const parts = reading?.includes?.filter(Boolean) || [];
  const miniParas = reading ? miniParagraphs(reading.mini) : [];
  const inCabinet = window.location.pathname.startsWith("/lk") && !isRobokassaReturn();

  if (inCabinet) {
    return <Cabinet />;
  }

  return (
    <div className="site">
      <div className="sparkles" aria-hidden="true">
        <span /><span /><span /><span /><span /><span />
      </div>
      <div className="orb one" />
      <div className="orb two" />
      <div className="shell">
        <header className={`topbar ${showLanding ? "topbar-landing" : "topbar-compact"}`}>
          <button className="brand" type="button" onClick={goHome} aria-label="Лея">
            {showLanding ? (
              <img className="brand-logo" src="/logo.jpg" alt="Лея" />
            ) : (
              <>
                <span className="brand-mark"><img src="/logo.jpg" alt="" /></span>
                <span>Лея</span>
              </>
            )}
          </button>
          <div className="topbar-right">
            {showLanding && (
              <nav className="topnav">
                <a href={cfg.legal_url} target="_blank" rel="noreferrer">Документы</a>
              </nav>
            )}
            {!showLanding && (
              <button className="nav-ghost" type="button" onClick={goHome}>На главную</button>
            )}
            <a className="nav-lk" href="/lk">Кабинет</a>
          </div>
        </header>

        {showLanding && (
          <Landing page={page} tab={tab} setTab={setTab} visible={visible} onPick={pickCard} />
        )}

        {!showLanding && (
          <div className="quiz-focus">
            <div className={`quiz-layout${screen >= 6 ? " reading" : ""}`}>
              <aside className="quiz-aside">
                <img src="/avatar.png" alt="" />
                <div>
                  <div className="eyebrow">{sel?.title || reading?.product_name || "Разбор"}</div>
                  <h3>{screen < 6 ? "Лея уже слушает" : "Твой разбор"}</h3>
                  <p>
                    {sel?.branch === "date"
                      ? "Матрица строится по дате. Карты здесь не нужны."
                      : sel?.branch === "pair"
                        ? "Две даты — и картина пары."
                        : "Держи вопрос в голове. Карты лягут на него."}
                  </p>
                </div>
              </aside>
              <div className={`quiz-frame${screen === 7 ? " offer-frame" : ""}${screen === 6 ? " mini-frame" : ""}`}>
                {screen === 2 && sel && q && (
                  <>
                    <div className="bar"><i style={{ width: `${((qi + 1) / sel.questions.length) * 100}%` }} /></div>
                    <div className="eyebrow">Вопрос {qi + 1} из {sel.questions.length}</div>
                    <div className="q">{q.text}</div>
                    <div className="opts">
                      {q.options.map((o) => (
                        <button key={o} className={`opt ${answers[qi] === o ? "on" : ""}`} onClick={() => chooseOpt(o)}>{o}</button>
                      ))}
                    </div>
                    <button className="btn" disabled={!answers[qi]} onClick={quizNext}>
                      {qi < sel.questions.length - 1 ? "Дальше" : sel.branch === "taro" ? "Готово" : "К расчёту"}
                    </button>
                    <p className="fine">Ни регистрации, ни телефона — только вопросы по делу</p>
                  </>
                )}

                {screen === 3 && sel && (
                  <div className="calm">
                    <div className="orb-pulse" />
                    <h3>{sel.tab === "rel" ? "Подумай о нём" : "Подумай о своём вопросе"}</h3>
                    <p className="sub">Не торопись. Держи это в голове — и нажми, когда будешь готова.</p>
                    <button className="btn" onClick={() => setScreen(4)}>Я готова</button>
                  </div>
                )}

                {screen === 4 && sel && (
                  <>
                    {sel.branch === "taro" && (
                      <>
                        <div className="eyebrow">Вытяни карты</div>
                        <div className="q">{sel.cards_n === 1 ? "Выбери одну карту" : "Выбери три карты, к которым потянуло"}</div>
                        <div className="picked">
                          {Array.from({ length: sel.cards_n }).map((_, i) => (
                            <div className="slot" key={i}>
                              {picks[i] ? <img src={deck.find((d) => d.slug === picks[i])?.image} alt="" /> : "✦"}
                            </div>
                          ))}
                        </div>
                        <div className="arc">
                          {deck.map((d, k) => {
                            const ang = (k - 3) * 11;
                            const off = (k - 3) * 42;
                            const dy = Math.abs(k - 3) * 7;
                            return (
                              <button
                                key={d.slug}
                                className={`back ${picks.includes(d.slug) ? "pick" : ""}`}
                                style={{ transform: `translate(-50%,-50%) translateX(${off}px) translateY(${dy}px) rotate(${ang}deg)` }}
                                onClick={() => togglePick(d.slug)}
                              >
                                ✦
                              </button>
                            );
                          })}
                        </div>
                        <button className="btn" disabled={picks.length < sel.cards_n} onClick={calculate}>
                          {picks.length < sel.cards_n ? `Выбрано ${picks.length} из ${sel.cards_n}` : "Смотреть расклад"}
                        </button>
                      </>
                    )}
                    {sel.branch === "date" && (
                      <>
                        <div className="eyebrow">Дата рождения</div>
                        <div className="q">Матрица строится по дате — карты здесь не нужны</div>
                        <div className="field"><label>Дата рождения</label><input className="inp" placeholder="дд.мм.гггг" value={birth} onChange={(e) => setBirth(e.target.value)} /></div>
                        <div className="field"><label>Город рождения</label><input className="inp" placeholder="не обязательно" value={city} onChange={(e) => setCity(e.target.value)} /></div>
                        <div className="field"><label>Время рождения — если знаешь</label><input className="inp" inputMode="numeric" maxLength={5} placeholder={TIME_PLACEHOLDER} value={time} onChange={(e) => setTime(maskTime(e.target.value))} /></div>
                        <button className="btn" disabled={!birth} onClick={() => { track("date_entered"); calculate(); }}>Построить матрицу</button>
                      </>
                    )}
                    {sel.branch === "pair" && (
                      <>
                        <div className="eyebrow">Две даты</div>
                        <div className="q">Совместимость считается по двум датам рождения</div>
                        <div className="field"><label>Твоя дата</label><input className="inp" placeholder="дд.мм.гггг" value={birth} onChange={(e) => setBirth(e.target.value)} /></div>
                        <div className="field"><label>Город рождения</label><input className="inp" placeholder="не обязательно" value={city} onChange={(e) => setCity(e.target.value)} /></div>
                        <div className="field"><label>Его дата</label><input className="inp" placeholder="дд.мм.гггг" value={partner} onChange={(e) => setPartner(e.target.value)} /></div>
                        <button className="btn" disabled={!birth || !partner} onClick={() => { track("date_entered"); calculate(); }}>Посчитать совместимость</button>
                      </>
                    )}
                    {err && <p className="err">{err}</p>}
                  </>
                )}

                {screen === 5 && (
                  <>
                    <div className="spin" />
                    <div className="h" style={{ textAlign: "center" }}>
                      {waitingPay
                        ? "Готовлю полный разбор"
                        : sel?.branch === "taro"
                          ? "Лея раскладывает карты"
                          : "Лея считает по дате"}
                    </div>
                    <p className="fine">
                      {waitingPay
                        ? "Оплата прошла — полный разбор откроется здесь, вход не нужен"
                        : "Пишу мини-разбор по твоим ответам. Это займёт несколько секунд."}
                    </p>
                  </>
                )}

                {screen === 6 && reading && (
                  <>
                    <div className="eyebrow">
                      {reading.branch === "taro"
                        ? `Твой расклад · ${(() => {
                            const n = (reading.mini.blocks || []).length || reading.drawn?.length || 0;
                            if (n === 1) return "1 карта";
                            if (n >= 2 && n <= 4) return `${n} карты`;
                            return n ? `${n} карт` : "карты";
                          })()}`
                        : reading.mini.title || reading.product_name}
                    </div>
                    {reading.branch === "taro" ? (
                      <div className="rc">
                        {(reading.mini.blocks || []).map((b) => (
                          <figure key={b.title} className={b.closed ? "closed" : undefined}>
                            {b.closed ? (
                              <div className="rc-back" aria-hidden="true">
                                <span>закрыта</span>
                              </div>
                            ) : (
                              b.image && <img src={b.image} alt="" />
                            )}
                            <figcaption>
                              {b.title}
                              {b.name ? <em>{b.name}</em> : null}
                            </figcaption>
                          </figure>
                        ))}
                      </div>
                    ) : reading.mini.stats?.percent ? (
                      <div className="mini-stats">
                        <div><b>{reading.mini.stats.percent}%</b><span>совместимость</span></div>
                        <div><b>{reading.mini.stats.life_paths}</b><span>числа пути</span></div>
                        <div><b>{reading.mini.stats.signs}</b><span>{reading.mini.stats.elements}</span></div>
                      </div>
                    ) : reading.mini.stats?.life_path ? (
                      <>
                        {reading.mini.stats.chart ? <MatrixChart chart={reading.mini.stats.chart} /> : null}
                        <div className="mini-stats">
                          <div><b>{reading.mini.stats.life_path}</b><span>число пути</span></div>
                          {reading.mini.stats.year_arcana ? (
                            <div><b>{reading.mini.stats.year_arcana}</b><span>аркан года</span></div>
                          ) : null}
                        </div>
                      </>
                    ) : (
                      <div className="mxn">
                        {(reading.mini.blocks || []).map((b) => (
                          <div className="open" key={b.title}>{b.title}</div>
                        ))}
                      </div>
                    )}
                    {reading.mini.pending ? (
                      <div className="mini-read pending">
                        <p>Лея дописывает разбор, загляни через минуту</p>
                        <button className="btn" type="button" onClick={retryMini}>Попробовать ещё раз</button>
                      </div>
                    ) : (
                      <article className="mini-read">
                        {miniParas.map((p, i) => (
                          <p
                            key={`${i}-${p.slice(0, 24)}`}
                            className={i === 0 ? "verdict" : i === miniParas.length - 1 && reading.mini.hook ? "hook" : undefined}
                            dangerouslySetInnerHTML={{ __html: mark(p) }}
                          />
                        ))}
                      </article>
                    )}
                    {!reading.mini.pending && !reading.mini.free && (
                      <div className="mini-cta">
                        <button className="btn gold" type="button" onClick={() => setScreen(7)}>{reading.mini.cta}</button>
                        <button className="btn link" type="button" onClick={() => goTelegramExit("mini")}>Пока не готова</button>
                      </div>
                    )}
                    {reading.mini.free && reading.card_id === "daily" && (
                      <button className="btn" type="button" onClick={() => goTelegramExit("mini")}>{reading.mini.cta}</button>
                    )}
                    <p className="fine">Мини уже здесь. Полный откроется сразу после оплаты — без регистрации.</p>
                    {err && <p className="err">{err}</p>}
                  </>
                )}

                {screen === 7 && reading && (
                  <>
                    <div className="eyebrow">{offer?.eyebrow || "Полный разбор"}</div>
                    <div className="h">{offer?.title || reading.mini.paywall_title || `Узнай полный «${reading.product_name}»`}</div>
                    <p className="sub">{offer?.subtitle || "Расклад откроется целиком, а потом ты задаёшь Лее вопросы по нему."}</p>
                    <ul className="pay-bullets">
                      {(reading.mini.paywall_bullets || parts).map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                    <p className="algo">
                      {offer?.algorithm || (reading.branch === "taro" ? cfg.paywall_algorithm_taro : cfg.paywall_algorithm_date)}
                    </p>
                    <div className="gift-block">
                      <p className="gift">{cfg.paywall_gift || offer?.gift}</p>
                      {(reading.mini.question_example || offer?.question_example || sel?.fallback_question) ? (
                        <p className="q-ex">
                          «{reading.mini.question_example || offer?.question_example || sel?.fallback_question}»
                        </p>
                      ) : null}
                    </div>
                    <div className="mini-cta">
                      <div className="pr pay-pr">
                        <div className="pay-row">
                          {offer?.show_strike && offer.strike_rub ? <s>{formatRub(offer.strike_rub)} ₽</s> : null}
                          <b>{formatRub(price)} ₽</b>
                        </div>
                        {offer?.show_strike ? (
                          <span className="cap">
                            {offer.price_caption || (reading.branch === "taro" ? cfg.paywall_price_caption_taro : cfg.paywall_price_caption_date)}
                          </span>
                        ) : null}
                      </div>
                      <button className="btn gold" type="button" disabled={paying} onClick={() => openPay("base")}>
                        {offer?.cta || `Открыть разбор за ${formatRub(price)} ₽`}
                      </button>
                      <p className="fine">{offer?.fine || "СБП или карта · без подписки · откроется сразу здесь"}</p>
                      <button className="btn link" type="button" onClick={() => goTelegramExit("paywall")}>Пока не готова</button>
                    </div>
                    {payOpen && (
                      <div className="modal" onClick={() => !paying && !payLive && setPayOpen(false)}>
                        <div className="mc pay-window" role="dialog" aria-modal="true" aria-label="Оплата" onClick={(e) => e.stopPropagation()}>
                          {payLive ? (
                            <>
                              <div className="eyebrow">Оплата</div>
                              <div className="h">Касса открыта рядом</div>
                              <p className="sub">
                                Оплати в окне Robokassa. Когда нажмёшь «вернуться в магазин», это окно закроется,
                                а полный разбор с чатом откроется здесь. Входить не нужно.
                              </p>
                              {payFrame ? (
                                <iframe className="pay-frame" title="Оплата Robokassa" src={payFrame} />
                              ) : (
                                <div className="spin" />
                              )}
                              <p className="fine">{waitingPay ? "Жду подтверждение оплаты…" : "Если окно кассы закрылось — нажми ещё раз."}</p>
                              <button
                                className="btn gold"
                                type="button"
                                disabled={paying}
                                onClick={() => {
                                  const url = payUrlRef.current || payFrame;
                                  if (!url) return;
                                  const launched = launchRobokassa(url, payPopup.current);
                                  payPopup.current = launched.popup;
                                  if (launched.iframe) setPayFrame(url);
                                }}
                              >
                                Открыть кассу ещё раз
                              </button>
                              <button className="btn link" type="button" onClick={() => { setPayLive(false); setPayOpen(false); }}>
                                Свернуть
                              </button>
                            </>
                          ) : (
                            <>
                          <div className="eyebrow">Оплата</div>
                          <div className="tar on">
                            <h4>{reading.product_name}</h4>
                            <div className="pr pay-pr">
                              <div className="pay-row">
                                {offer?.show_strike && offer.strike_rub ? <s>{formatRub(offer.strike_rub)} ₽</s> : null}
                                <b>{formatRub(payAmount)} ₽</b>
                              </div>
                              {offer?.show_strike ? (
                                <span className="cap">
                                  {offer.price_caption || (reading.branch === "taro" ? cfg.paywall_price_caption_taro : cfg.paywall_price_caption_date)}
                                </span>
                              ) : null}
                            </div>
                          </div>
                          <ConsentBoxes priv={priv} mkt={mkt} setPriv={setPriv} setMkt={setMkt} marketing={false} />
                          <button className="btn gold" disabled={paying || !priv} onClick={pay}>
                            {paying ? "Открываю оплату…" : `Оплатить ${formatRub(payAmount)} ₽`}
                          </button>
                          {!priv && <p className="fine">Отметь согласие - и откроется страница оплаты.</p>}
                          {err && <p className="err">{err}</p>}
                          <p className="fine">Карта или СБП. Разбор откроется на этой странице — без входа в кабинет.</p>
                          <button className="btn link" type="button" disabled={paying} onClick={() => setPayOpen(false)}>Назад</button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {screen === 8 && reading && (
                  <>
                    <div className="eyebrow">Разбор готов</div>
                    <div className="h">{reading.mini.title}</div>
                    {reading.paid_html ? (
                      <article className="stream md" dangerouslySetInnerHTML={{ __html: reading.paid_html }} />
                    ) : (
                      <div className="stream">{stream || "Готовлю текст…"}<span className="cursor" /></div>
                    )}
                    {(reading.paid_html || (reading.paid_text && stream.length >= reading.paid_text.length)) ? (
                    <section className="ask-leia">
                      <div className="eyebrow">Спроси Лею по разбору</div>
                      <div className="chat-log">
                        {askLog.map((row, i) => (
                          <div key={i} className={`chat-bubble ${row.role === "user" ? "me" : "leia"}`}>
                            {row.role === "leia" ? <LeiaText text={row.text} html={row.html} /> : row.text}
                          </div>
                        ))}
                        {asking && (
                          <div className="chat-bubble leia typing" aria-live="polite">
                            <span className="typing-label">Лея пишет</span>
                            <span className="typing-dots"><span /><span /><span /></span>
                          </div>
                        )}
                      </div>
                      {needPack || askLeft === 0 ? (
                        <div className="q-packs">
                          <p className="sub">Бесплатные вопросы закончились. Можно докупить.</p>
                          <button className="btn" type="button" disabled={paying} onClick={() => buyQuestions("q1")}>
                            1 вопрос за {cfg.question_price_rub} ₽
                          </button>
                          <button className="btn gold" type="button" disabled={paying} onClick={() => buyQuestions("q5")}>
                            5 вопросов за {cfg.question_pack5_price_rub} ₽
                          </button>
                        </div>
                      ) : (
                        <div className="chat-compose">
                          <input
                            className="inp"
                            value={askText}
                            disabled={asking}
                            onChange={(e) => setAskText(e.target.value)}
                            placeholder={asking ? "Лея ещё отвечает…" : "Спроси по разбору"}
                            onKeyDown={(e) => e.key === "Enter" && !asking && askLeia()}
                          />
                          <button className="btn" type="button" disabled={asking || paying || !askText.trim()} onClick={askLeia}>
                            {asking ? "Пишет…" : "Спросить"}
                          </button>
                        </div>
                      )}
                      {askLeft != null ? <p className="fine">Осталось {askLeft} из {reading.question_budget || cfg.question_free_limit}</p> : null}
                    </section>
                    ) : null}
                    <p className="fine">Ссылка на этот разбор работает год. Сохрани её — вход не обязателен.</p>
                  </>
                )}

                {screen === 9 && reading && (
                  <>
                    <div className="eyebrow">Смена ветки</div>
                    <div className="h">
                      {reading.branch === "taro"
                        ? "Карты показали, что происходит. Матрица покажет, почему это повторяется"
                        : "Матрица показала структуру. Карты покажут, что происходит прямо сейчас"}
                    </div>
                    <div className="tar on">
                      <h4>{reading.branch === "taro" ? "Матрица судьбы" : "Расклад на месяц"}</h4>
                      <div className="pr">{reading.branch === "taro" ? "690" : "390"} ₽</div>
                    </div>
                    <button className="btn gold" disabled={paying} onClick={() => buy("upsell")}>
                      {paying ? "Открываю оплату…" : "Посчитать"}
                    </button>
                    <button className="btn link" onClick={() => setScreen(10)}>Не сейчас</button>
                  </>
                )}

                {screen === 10 && (
                  <>
                    <div className="eyebrow">Пакет</div>
                    <div className="h">Месяц безлимита вместо одного разбора</div>
                    <div className="sub-card">
                      <h4>Безлимит на месяц</h4>
                      <div className="pr">590 ₽ <em>/ месяц</em></div>
                      <p>Сайтовые разборы без лимита. VIP бота этим платежом не открывается.</p>
                    </div>
                    <p className="sub">
                      590 ₽ сейчас, дальше 590 ₽ каждые 30 дней, пока не отменишь. Напомним на почту за день до списания. Отменить — в кабинете в один клик.
                    </p>
                    {(!loggedIn || !email) && (
                      <div className="field">
                        <label>Почта — на неё придёт напоминание за сутки до списания</label>
                        <input className="inp" type="email" placeholder="ты@почта.ru" value={email} onChange={(e) => setEmail(e.target.value)} />
                      </div>
                    )}
                    <ConsentBoxes priv={priv} mkt={mkt} setPriv={setPriv} setMkt={setMkt} />
                    <label className={`chk ${recur ? "on" : ""}`} onClick={() => setRecur(!recur)}>
                      <i />
                      <span>
                        Согласна на автоматическое списание 590 ₽ каждые 30 дней с этой карты или счёта по{" "}
                        <a href="/legal#subscription" onClick={(e) => e.stopPropagation()}>условиям подписки</a>
                      </span>
                    </label>
                    <button className="btn gold" disabled={paying || !recur || !priv} onClick={() => buy("unlimited")}>
                      {paying ? "Открываю оплату…" : "Подключить безлимит"}
                    </button>
                    <button className="btn link" onClick={() => setScreen(11)}>Пока без подписки</button>
                    {err && <p className="err">{err}</p>}
                  </>
                )}

                {screen === 11 && (
                  <>
                    <div className="eyebrow">Лея в Telegram</div>
                    <div className="h">Если хочется диалога и более глубокого разбора ситуаций</div>
                    <p className="sub">Это ИИ-бот Лея, не живой таролог. Он помнит историю и доступен ночью.</p>
                    <div className="feat"><div><b>Помнит всю твою историю</b><span> Не нужно каждый раз объяснять заново</span></div></div>
                    <div className="feat"><div><b>Разберёт вашу переписку</b><span> Скриншот — и подтекст его слов</span></div></div>
                    <div className="feat"><div><b>Всегда на связи</b><span> Ночью и в выходные</span></div></div>
                    <div className="feat"><div><b>Карта дня каждое утро</b><span> Короткая подсказка приходит сама</span></div></div>
                    <button className="btn" onClick={() => { track("bot_open", reading ? readingTrack(reading) : undefined); setVpn(true); }}>Открыть в Telegram</button>
                    <button className="btn link" onClick={() => setScreen(12)}>Позже</button>
                    {vpn && (
                      <div className="modal" onClick={() => setVpn(false)}>
                        <div className="mc" onClick={(e) => e.stopPropagation()}>
                          <h4>Включи VPN перед переходом</h4>
                          <p>В России Telegram не открывается без VPN. Если приложение не запустится - включи VPN и нажми ещё раз.</p>
                          <a className="btn" href={`https://t.me/${cfg.bot_username}?start=web_${reading?.token || ""}`}>Открыть в Telegram</a>
                          <button className="btn link" onClick={() => setVpn(false)}>Вернусь позже</button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {screen === 12 && (
                  <>
                    <div className="eyebrow">Последний шаг</div>
                    <div className="h">Куда прислать разбор?</div>
                    <p className="sub">Ссылка живёт год — откроешь даже с другого телефона</p>
                    <div className="field"><label>Почта</label><input className="inp" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                    <ConsentBoxes priv={priv} mkt={mkt} setPriv={setPriv} setMkt={setMkt} />
                    <button
                      className="btn"
                      disabled={!priv || !email.trim()}
                      onClick={async () => {
                        if (reading) {
                          await api(`/api/web/readings/${reading.token}/contact`, {
                            method: "POST",
                            body: JSON.stringify({ email, marketing: mkt, privacy: priv }),
                          });
                          track("contact_left");
                        }
                        goHome();
                      }}
                    >
                      Сохранить и открыть разбор
                    </button>
                    <p className="fine">Первая галочка обязательна, чтобы отправить разбор на почту. Рассылка — только если отметишь вторую.</p>
                    <button className="btn link" type="button" onClick={goHome}>Открыть без почты</button>
                  </>
                )}

                {screen === 13 && (
                  <>
                    <div className="eyebrow">Лея в Telegram</div>
                    <div className="h">{exitFrom === "paywall" ? "Разбор подождёт. Бот уже знает запрос" : "Бот уже знает твой запрос"}</div>
                    <p className="sub">Это ИИ-бот Лея, не живой таролог. Он помнит историю и отвечает ночью.</p>
                    {reading?.mini.tg_question_example ? <p className="q-ex">{reading.mini.tg_question_example}</p> : null}
                    <button className="btn" type="button" onClick={() => { track("bot_open", reading ? readingTrack(reading) : undefined); setVpn(true); }}>
                      Открыть в Telegram
                    </button>
                    <a className="btn ghost" href="/lk" onClick={() => track("cabinet_click")}>Личный кабинет</a>
                    {vpn && (
                      <div className="modal" onClick={() => setVpn(false)}>
                        <div className="mc" onClick={(e) => e.stopPropagation()}>
                          <h4>Включи VPN перед переходом</h4>
                          <p>В России Telegram не открывается без VPN. Если приложение не запустится - включи VPN и нажми ещё раз.</p>
                          <a className="btn" href={`https://t.me/${cfg.bot_username}?start=web_${reading?.token || ""}`}>Открыть в Telegram</a>
                          <button className="btn link" onClick={() => setVpn(false)}>Вернусь позже</button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {screen === 14 && (
                  <>
                    <div className="eyebrow">Лимит на сегодня</div>
                    <div className="h">Сегодня уже пять мини-разборов с этого телефона</div>
                    <p className="sub">Полный разбор и вопросы Лее остаются. Завтра мини снова будут доступны.</p>
                    <button className="btn" type="button" onClick={() => { track("bot_open"); setVpn(true); }}>Открыть в Telegram</button>
                    <a className="btn ghost" href="/lk" onClick={() => track("cabinet_click")}>Личный кабинет</a>
                    {vpn && (
                      <div className="modal" onClick={() => setVpn(false)}>
                        <div className="mc" onClick={(e) => e.stopPropagation()}>
                          <h4>Включи VPN перед переходом</h4>
                          <p>В России Telegram не открывается без VPN.</p>
                          <a className="btn" href={`https://t.me/${cfg.bot_username}`}>Открыть в Telegram</a>
                          <button className="btn link" onClick={() => setVpn(false)}>Вернусь позже</button>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {err && screen !== 4 && screen !== 7 && screen !== 10 && <p className="err">{err}</p>}
              </div>
            </div>
          </div>
        )}
        <SiteFooter />
        <CookieBanner />
      </div>
    </div>
  );
}
