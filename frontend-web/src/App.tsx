import { useEffect, useMemo, useState } from "react";
import { api, guestId, track, utm } from "./api";
import { Cabinet } from "./Cabinet";
import { Landing } from "./Landing";

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
};

type Mini = {
  mirror: string;
  blocks: { title: string; text: string; image?: string; name?: string }[];
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
  paid_text?: string;
};

export function App() {
  const tokenFromPath = window.location.pathname.startsWith("/r/")
    ? window.location.pathname.slice(3)
    : "";
  const [cards, setCards] = useState<Card[]>([]);
  const [cfg, setCfg] = useState({ bot_username: "astro_leia_bot", legal_url: "/legal" });
  const [tab, setTab] = useState("rel");
  const [screen, setScreen] = useState(tokenFromPath ? 8 : 1);
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
  const [tariff, setTariff] = useState<"base" | "bundle">("bundle");
  const [err, setErr] = useState("");
  const [vpn, setVpn] = useState(false);
  const [mkt, setMkt] = useState(false);
  const [priv, setPriv] = useState(false);
  const [recur, setRecur] = useState(false);
  const [stream, setStream] = useState("");
  const [paying, setPaying] = useState(false);

  const showLanding = screen === 1 && !tokenFromPath;

  useEffect(() => {
    api<{ cards: Card[] }>("/api/web/cards").then((d) => setCards(d.cards));
    api<typeof cfg>("/api/web/config").then(setCfg);
    api("/api/web/sessions", {
      method: "POST",
      body: JSON.stringify({ guest_id: guestId(), utm: utm() }),
    }).catch(() => undefined);
    if (tokenFromPath) {
      api<Reading>(`/api/web/readings/${tokenFromPath}`)
        .then((r) => {
          setReading(r);
          setScreen(r.paid ? 8 : 6);
        })
        .catch(() => setErr("Ссылка не найдена или истекла"));
    }
  }, [tokenFromPath]);

  useEffect(() => {
    if (screen === 8 && reading?.paid_text) {
      let i = 0;
      const text = reading.paid_text;
      const id = window.setInterval(() => {
        i += 4;
        setStream(text.slice(0, i));
        if (i >= text.length) window.clearInterval(id);
      }, 16);
      return () => window.clearInterval(id);
    }
    return undefined;
  }, [screen, reading?.paid_text]);

  const q = sel?.questions[qi];
  const visible = useMemo(
    () => cards.filter((c) => c.tab === tab),
    [cards, tab],
  );

  function goHome() {
    setScreen(1);
    setSel(null);
    setReading(null);
    setErr("");
    window.history.replaceState({}, "", "/");
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
    setErr("");
    setScreen(5);
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
          utm: utm(),
        }),
      });
      setReading(r);
      track("calc_done");
      await new Promise((res) => setTimeout(res, 1600));
      setScreen(6);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Не получилось");
      setScreen(4);
    }
  }

  async function pay() {
    if (!reading || paying) return;
    setErr("");
    setPaying(true);
    track("checkout_start");
    try {
      const r = await api<{ payment_url?: string; demo?: boolean; token: string }>(
        `/api/web/readings/${reading.token}/checkout`,
        { method: "POST", body: JSON.stringify({ tariff }) },
      );
      if (r.payment_url) {
        window.location.href = r.payment_url;
        return;
      }
      const full = await api<Reading>(`/api/web/readings/${r.token}`);
      setReading(full);
      window.history.replaceState({}, "", `/r/${r.token}`);
      track("purchase");
      setScreen(8);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Оплата не прошла");
    } finally {
      setPaying(false);
    }
  }

  async function buy(kind: "upsell" | "unlimited") {
    if (!reading || paying) return;
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
          body: JSON.stringify({ tariff: kind, recur_consent: recur }),
        },
      );
      if (r.payment_url) {
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
  const bundle = price + 300;
  const inCabinet = window.location.pathname.startsWith("/lk");

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
        <header className="topbar">
          <button className="brand" type="button" onClick={goHome} aria-label="Лея">
            <span className="brand-mark"><img src="/avatar.png" alt="" /></span>
            <span>Лея</span>
          </button>
          {showLanding ? (
            <nav className="topnav">
              <a href="#how">Как это работает</a>
              <a href="#quiz">Разбор</a>
              <a href="/lk">Кабинет</a>
              <a href={cfg.legal_url}>Документы</a>
            </nav>
          ) : (
            <button className="nav-ghost" type="button" onClick={goHome}>На главную</button>
          )}
        </header>

        {showLanding && (
          <Landing cfg={cfg} tab={tab} setTab={setTab} visible={visible} onPick={pickCard} />
        )}

        {!showLanding && (
          <div className="quiz-focus">
            <div className="quiz-layout">
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
              <div className="quiz-frame">
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
                        <div className="field"><label>Время рождения — если знаешь</label><input className="inp" placeholder="не обязательно" value={time} onChange={(e) => setTime(e.target.value)} /></div>
                        <button className="btn" disabled={!birth} onClick={() => { track("date_entered"); calculate(); }}>Построить матрицу</button>
                      </>
                    )}
                    {sel.branch === "pair" && (
                      <>
                        <div className="eyebrow">Две даты</div>
                        <div className="q">Совместимость считается по двум датам рождения</div>
                        <div className="field"><label>Твоя дата</label><input className="inp" placeholder="дд.мм.гггг" value={birth} onChange={(e) => setBirth(e.target.value)} /></div>
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
                    <div className="h" style={{ textAlign: "center" }}>{sel?.branch === "taro" ? "Лея раскладывает карты" : "Лея считает по дате"}</div>
                    <div className="field"><label>Прислать разбор, чтобы не потерять?</label><input className="inp" placeholder="твоя почта" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                    <p className="fine">Можно пропустить — результат откроется здесь</p>
                  </>
                )}

                {screen === 6 && reading && (
                  <>
                    <div className="eyebrow">{reading.branch === "taro" ? "Твой расклад готов" : "Расчёт готов"}</div>
                    <div className="h">{reading.mini.title}</div>
                    <p className="sub">{reading.mini.lead}</p>
                    {reading.branch === "taro" ? (
                      <div className="rc">
                        {(reading.mini.blocks || []).map((b) => (
                          <figure key={b.title}>
                            {b.image && <img src={b.image} alt="" />}
                            <figcaption>{b.title}</figcaption>
                          </figure>
                        ))}
                      </div>
                    ) : (
                      <div className="mxn">
                        {(reading.mini.blocks || []).map((b) => (
                          <div className="open" key={b.title}>{b.title}</div>
                        ))}
                      </div>
                    )}
                    <div className="txt">
                      <p>{reading.mini.mirror}</p>
                      {(reading.mini.blocks || []).slice(0, 2).map((b, i) => (
                        <div key={b.title} className={i === 1 && reading.mini.fade ? "fade" : undefined}>
                          <p dangerouslySetInnerHTML={{ __html: b.text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>") }} />
                        </div>
                      ))}
                    </div>
                    {!reading.mini.free && <div className="lock">{reading.mini.cut}</div>}
                    {reading.mini.free && reading.card_id === "daily" && (
                      <button className="btn" onClick={() => setScreen(10)}>{reading.mini.cut}</button>
                    )}
                    {!reading.mini.free && (
                      <button className="btn" onClick={() => { track("paywall_view"); setScreen(7); }}>{reading.mini.cta}</button>
                    )}
                    {reading.mini.free && reading.card_id === "other" && (
                      <button className="btn" onClick={() => { track("paywall_view"); setScreen(7); }}>Открыть полный разбор</button>
                    )}
                    <a className="btn ghost" href={`/lk?reading=${reading.token}`}>Сохранить в кабинете</a>
                  </>
                )}

                {screen === 7 && reading && (
                  <>
                    <div className="h">Полный разбор</div>
                    <p className="sub">Десять блоков вместо трёх абзацев</p>
                    <div className={`tar ${tariff === "base" ? "on" : ""}`} onClick={() => setTariff("base")}>
                      <h4>{reading.product_name}</h4>
                      <div className="pr">{price} ₽</div>
                    </div>
                    <div className={`tar ${tariff === "bundle" ? "on" : ""}`} onClick={() => setTariff("bundle")}>
                      <span className="tag">Выгоднее</span>
                      <h4>{reading.product_name} + доп. разбор</h4>
                      <div className="pr">{bundle} ₽ <s>{price + 590} ₽</s></div>
                    </div>
                    <div className="pay"><span className="on">СБП</span><span>Карта</span></div>
                    <button className="btn gold" disabled={paying} onClick={pay}>
                      {paying ? "Открываю оплату…" : `Оплатить ${tariff === "bundle" ? bundle : price} ₽`}
                    </button>
                    {err && <p className="err">{err}</p>}
                    <p className="fine">Без подписок и автосписаний. Это разовый разбор с сайта.</p>
                    <a className="btn ghost" href={`/lk?reading=${reading.token}`}>Сначала войти в кабинет</a>
                  </>
                )}

                {screen === 8 && reading && (
                  <>
                    <div className="eyebrow">Разбор готов</div>
                    <div className="h">{reading.mini.title}</div>
                    <div className="stream">{stream || "Готовлю текст…"}<span className="cursor" /></div>
                    <button className="btn" onClick={() => { track("upsell_view"); setScreen(9); }}>Что дальше</button>
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
                    <label className={`chk ${recur ? "on" : ""}`} onClick={() => setRecur(!recur)}>
                      <i />
                      <span>Согласна на списание 590 ₽ раз в 30 дней. Отмена в один клик через поддержку.</span>
                    </label>
                    <button className="btn gold" disabled={paying} onClick={() => buy("unlimited")}>
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
                    <button className="btn" onClick={() => { track("bot_open"); setVpn(true); }}>Открыть Лею в Telegram</button>
                    <button className="btn link" onClick={() => setScreen(12)}>Позже</button>
                    {vpn && (
                      <div className="modal" onClick={() => setVpn(false)}>
                        <div className="mc" onClick={(e) => e.stopPropagation()}>
                          <h4>Включи VPN перед переходом</h4>
                          <p>В России Telegram не открывается без VPN. Если приложение не запустится — включи VPN и нажми ещё раз.</p>
                          <a className="btn" href={`https://t.me/${cfg.bot_username}?start=web_${reading?.token || ""}`}>Всё равно открыть</a>
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
                    <label className={`chk ${mkt ? "on" : ""}`} onClick={() => setMkt(!mkt)}><i /><span>Согласна получать разборы и предложения. Отписаться можно в один клик</span></label>
                    <label className={`chk ${priv ? "on" : ""}`} onClick={() => setPriv(!priv)}><i /><span>Согласна с <a href={cfg.legal_url}>политикой обработки персональных данных</a></span></label>
                    <button
                      className="btn"
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
                    <p className="fine">Без галочки согласия разбор всё равно откроется — рассылка просто не придёт</p>
                  </>
                )}

                {err && screen !== 4 && screen !== 7 && screen !== 10 && <p className="err">{err}</p>}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
