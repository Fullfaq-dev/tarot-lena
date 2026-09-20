type CardLite = {
  id: string;
  tab: string;
  title: string;
  icon: string;
};

type Props<T extends CardLite> = {
  cfg: { bot_username: string; legal_url: string };
  tab: string;
  setTab: (tab: string) => void;
  visible: T[];
  onPick: (card: T) => void;
};

export function Landing<T extends CardLite>({ cfg, tab, setTab, visible, onPick }: Props<T>) {
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">✦ Таро и матрица судьбы — сразу на сайте</p>
          <h1>
            Разберись в ситуации,
            <span>не объясняя её боту</span>
          </h1>
          <p className="hero-copy">
            Выбери, что происходит. Ответь на три коротких вопроса. Лея покажет кусок расклада
            бесплатно — полный разбор откроется здесь же, без регистрации.
          </p>
          <div className="cta-row">
            <a className="cta-primary" href="#quiz">
              Получить разбор
            </a>
            <a className="cta-secondary" href="#how">
              Как это работает
            </a>
          </div>
          <div className="trust-row">
            <div className="trust-pill">
              <strong>0 ₽</strong>
              мини-разбор до оплаты
            </div>
            <div className="trust-pill">
              <strong>3 мин</strong>
              от вопроса до карт
            </div>
            <div className="trust-pill">
              <strong>год</strong>
              ссылка на разбор живёт
            </div>
          </div>
        </div>
        <div className="portal-card" aria-hidden="true">
          <div className="mystic-avatar">
            <img src="/avatar.png" alt="" />
          </div>
          <div className="floating-note left">
            <strong>Без Telegram на старте</strong>
            Сначала сайт. Бот — если захочешь диалог.
          </div>
          <div className="floating-note right">
            <strong>Карты и дата</strong>
            Расклад или матрица — под твою ситуацию.
          </div>
        </div>
      </section>

      <section className="section" id="how">
        <div className="section-title">
          <h2>Четыре шага, без анкеты</h2>
          <p>Ни телефона, ни почты, ни аккаунта. Почту можно оставить потом — чтобы не потерять ссылку.</p>
        </div>
        <div className="flow">
          <article className="flow-card">
            <h3>Ситуация</h3>
            <p>Любовь, возврат, деньги, работа или карта дня — как в живом разговоре, только короче.</p>
          </article>
          <article className="flow-card">
            <h3>Вопросы</h3>
            <p>Три уточнения, чтобы Лея не гадала в пустоту. Для матрицы — дата рождения.</p>
          </article>
          <article className="flow-card">
            <h3>Мини-разбор</h3>
            <p>Зеркало ситуации и открытые блоки. Дальше текст обрывается — это и есть бесплатная часть.</p>
          </article>
          <article className="flow-card">
            <h3>Полный текст</h3>
            <p>Разовый платёж на сайте. Ссылка на год. Telegram — по желанию, это ИИ, не живой таролог.</p>
          </article>
        </div>
      </section>

      <section className="section" id="quiz">
        <div className="section-title">
          <h2>Что тебя сейчас волнует?</h2>
          <p>Нажми карточку — квиз начнётся здесь, на этой же странице.</p>
        </div>
        <div className="quiz-intro">
          <div className="tabs">
            <button className={`tab ${tab === "rel" ? "on" : ""}`} onClick={() => setTab("rel")}>
              Про отношения
            </button>
            <button className={`tab ${tab === "me" ? "on" : ""}`} onClick={() => setTab("me")}>
              Про меня
            </button>
          </div>
          <div className="cards landing-cards">
            {visible.map((c) => (
              <button key={c.id} className="c" onClick={() => onPick(c)}>
                <span className="ic">{c.icon}</span>
                <b>{c.title}</b>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="more">
        <div className="section-title">
          <h2>После оплаты можно глубже</h2>
          <p>Сайт закрывает разовую ситуацию. Если нужен диалог, история и утренние подсказки — Лея есть в Telegram.</p>
        </div>
        <div className="feature-grid">
          <article className="feature-card">
            <h3>Помнит контекст</h3>
            <p>Не надо каждый раз заново рассказывать, кто он и что случилось на прошлой неделе.</p>
          </article>
          <article className="feature-card">
            <h3>Разбор переписки</h3>
            <p>Скриншоты диалога — Лея читает подтекст, а не только то, что он написал вслух.</p>
          </article>
          <article className="feature-card">
            <h3>На связи ночью</h3>
            <p>Это ИИ-бот, не человек. Поэтому отвечает в три часа ночи так же, как в полдень.</p>
          </article>
        </div>
        <div className="wide-cta">
          <h2>Сначала разбор на сайте</h2>
          <p>
            Открой карточку выше. Бот подождёт — и сам подхватит историю, если перейдёшь
            по ссылке после оплаты.
          </p>
          <div className="cta-row">
            <a className="cta-primary" href="#quiz">
              Выбрать ситуацию
            </a>
            <a className="cta-secondary" href={`https://t.me/${cfg.bot_username}?start=landing`}>
              @{cfg.bot_username}
            </a>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        © Лея · таро и нумерология · <a href={cfg.legal_url}>Документы</a>
        {" · "}
        <a href={`https://t.me/${cfg.bot_username}`}>Поддержка</a>
      </footer>
    </>
  );
}
