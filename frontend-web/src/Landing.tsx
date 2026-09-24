import { useState } from "react";

type CardLite = {
  id: string;
  tab: string;
  title: string;
  icon: string;
};

export type LandingPage = "home" | "taro" | "matrica" | "sovmestimost";

const COPY: Record<LandingPage, { h1: string; paragraphs: string[]; tabs: boolean }> = {
  home: {
    h1: "Что тебя сейчас волнует?",
    paragraphs: [
      "Выбери карточку — разбор начнётся сразу, без анкеты и без Telegram.",
      "Отношения, матрица судьбы, деньги или совместимость по двум датам.",
    ],
    tabs: true,
  },
  taro: {
    h1: "Расклад на твой вопрос",
    paragraphs: [
      "Карты на чувства, возврат и замужество. Три коротких ответа — и Лея показывает, что лежит на ситуации.",
      "Это не общий гороскоп: расклад строится под твой вопрос.",
    ],
    tabs: false,
  },
  matrica: {
    h1: "Матрица судьбы по дате рождения",
    paragraphs: [
      "Нумерология и матрица по дате: сценарий отношений, деньги и предназначение.",
      "Дата рождения уже говорит, откуда повторяется одно и то же.",
    ],
    tabs: false,
  },
  sovmestimost: {
    h1: "Совместимость по двум датам",
    paragraphs: [
      "Две даты рождения — и видно, в чём вы совпадаете, а где начинаются ссоры.",
      "Не по именам и не по знаку в общем гороскопе. Считается ваша пара.",
    ],
    tabs: false,
  },
};

type Props<T extends CardLite> = {
  page: LandingPage;
  tab: string;
  setTab: (tab: string) => void;
  visible: T[];
  onPick: (card: T) => void;
};

export function Landing<T extends CardLite>({ page, tab, setTab, visible, onPick }: Props<T>) {
  const copy = COPY[page];
  return (
    <section className="section entry">
      <div className="section-title">
        <h1>{copy.h1}</h1>
        {copy.paragraphs.map((text) => (
          <p key={text}>{text}</p>
        ))}
      </div>
      <div className="quiz-intro">
        {copy.tabs && (
          <div className="tabs">
            <button className={`tab ${tab === "rel" ? "on" : ""}`} type="button" onClick={() => setTab("rel")}>
              Про отношения
            </button>
            <button className={`tab ${tab === "me" ? "on" : ""}`} type="button" onClick={() => setTab("me")}>
              Про меня
            </button>
          </div>
        )}
        <div className="cards landing-cards">
          {visible.map((c) => (
            <button key={c.id} className="c" type="button" onClick={() => onPick(c)}>
              <span className="ic">{c.icon}</span>
              <b>{c.title}</b>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

const GUIDE = [
  {
    title: "Выбери, что волнует",
    text: "На главной сразу карточки. Нажала — и разбор уже начался, без анкеты и без регистрации.",
  },
  {
    title: "Ответь на пару вопросов",
    text: "Три коротких уточнения. Для матрицы и совместимости вместо карт нужна дата рождения.",
  },
  {
    title: "Прочитай бесплатную часть",
    text: "Лея показывает начало разбора. Дальше текст обрывается — видно, что внутри, но не всё.",
  },
  {
    title: "Открой полный текст",
    text: "Разовый платёж, без подписки. Ссылка живёт год. Telegram можно подключить потом, если захочешь диалог.",
  },
] as const;

const SAMPLE_CARDS = ["Вернётся ли он?", "Почему я одна?", "Наша совместимость"];
const SAMPLE_ANSWERS = ["Меньше месяца", "Один-три месяца", "Больше года"];

export function HowItWorks({
  legalUrl,
  bot,
  onClose,
}: {
  legalUrl: string;
  bot: string;
  onClose?: () => void;
}) {
  const [step, setStep] = useState(0);
  const [card, setCard] = useState(SAMPLE_CARDS[0]);
  const [answer, setAnswer] = useState(SAMPLE_ANSWERS[0]);
  const current = GUIDE[step];

  return (
    <section className="guide">
      <div className="guide-head">
        <div>
          <h1>Как это работает</h1>
          <p>Четыре шага. Можно понажимать — это пример, не настоящий разбор.</p>
        </div>
        {onClose && (
          <button className="guide-x" type="button" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        )}
      </div>
      <div className="guide-dots" role="tablist">
        {GUIDE.map((item, index) => (
          <button
            key={item.title}
            type="button"
            className={index === step ? "on" : ""}
            onClick={() => setStep(index)}
          >
            {index + 1}. {item.title}
          </button>
        ))}
      </div>
      <div className="guide-body">
        <div>
          <h2>{current.title}</h2>
          <p>{current.text}</p>
          <div className="guide-nav">
            <button className="btn ghost" type="button" disabled={step === 0} onClick={() => setStep(step - 1)}>
              Назад
            </button>
            {step < GUIDE.length - 1 ? (
              <button className="btn" type="button" onClick={() => setStep(step + 1)}>
                Дальше
              </button>
            ) : (
              <a className="btn" href="/" onClick={onClose}>
                К разборам
              </a>
            )}
          </div>
        </div>
        <div className="guide-stage">
          {step === 0 &&
            SAMPLE_CARDS.map((title) => (
              <button key={title} type="button" className={`c ${card === title ? "on" : ""}`} onClick={() => setCard(title)}>
                <b>{title}</b>
              </button>
            ))}
          {step === 1 && (
            <>
              <p className="guide-q">Как давно вы расстались?</p>
              {SAMPLE_ANSWERS.map((title) => (
                <button key={title} type="button" className={`opt ${answer === title ? "on" : ""}`} onClick={() => setAnswer(title)}>
                  {title}
                </button>
              ))}
            </>
          )}
          {step === 2 && (
            <div className="guide-mini">
              <b>{card}</b>
              <p>Он не пропал из-за равнодушия. Пауза держится на страхе сказать прямо, и это уже видно по первым картам.</p>
              <div className="lock">Дальше — почему это повторяется и что делать на этой неделе.</div>
            </div>
          )}
          {step === 3 && (
            <div className="guide-mini">
              <b>Полный разбор</b>
              <p>Десять блоков вместо трёх абзацев. Ссылка останется в кабинете.</p>
              <div className="tar on">
                <h4>{card}</h4>
                <div className="pr">590 ₽</div>
              </div>
            </div>
          )}
        </div>
      </div>
      <p className="sub guide-links">
        <a href="/">К разборам</a>
        {" · "}
        <a href="/lk">Кабинет</a>
        {" · "}
        <a href={legalUrl}>Документы</a>
        {" · "}
        <a href={`https://t.me/${bot}`}>Поддержка</a>
      </p>
    </section>
  );
}
