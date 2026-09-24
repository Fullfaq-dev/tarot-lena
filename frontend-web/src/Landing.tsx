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

export function HowItWorks({ legalUrl, bot }: { legalUrl: string; bot: string }) {
  return (
    <section className="section">
      <div className="section-title">
        <h1>Как это работает</h1>
        <p>Четыре шага. Почту можно оставить потом — чтобы не потерять ссылку.</p>
      </div>
      <div className="flow">
        <article className="flow-card">
          <h3>Ситуация</h3>
          <p>Любовь, возврат, деньги, работа или карта дня.</p>
        </article>
        <article className="flow-card">
          <h3>Вопросы</h3>
          <p>Три уточнения. Для матрицы — дата рождения.</p>
        </article>
        <article className="flow-card">
          <h3>Мини-разбор</h3>
          <p>Открытая часть бесплатно. Дальше текст обрывается.</p>
        </article>
        <article className="flow-card">
          <h3>Полный текст</h3>
          <p>Разовый платёж. Ссылка живёт год. Telegram — по желанию.</p>
        </article>
      </div>
      <p className="sub" style={{ marginTop: 24 }}>
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
