import { useEffect, useState } from "react";

const COOKIE_KEY = "leia_cookies";

declare global {
  interface Window {
    leiaInitMetrika?: () => void;
  }
}

export function SiteFooter() {
  return (
    <footer className="site-foot">
      <p>
        Карпова Елена Игоревна, самозанятая, ИНН 234594723806 ·{" "}
        <a href="mailto:elenakarpva@gmail.com">elenakarpva@gmail.com</a> · +7 926 777-69-85
      </p>
      <p>
        <a href="/legal#offer">Оферта</a>
        {" · "}
        <a href="/legal#privacy">Политика ПДн</a>
        {" · "}
        <a href="/legal#consent">Согласие на обработку ПДн</a>
      </p>
      <p>Сервис для лиц старше 18 лет. Разборы создаются с помощью ИИ и носят развлекательный характер.</p>
    </footer>
  );
}

export function CookieBanner() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      setOpen(!localStorage.getItem(COOKIE_KEY));
    } catch {
      setOpen(true);
    }
  }, []);

  function choose(mode: "all" | "needed") {
    try {
      localStorage.setItem(COOKIE_KEY, mode);
    } catch {
      /* ignore */
    }
    if (mode === "all") window.leiaInitMetrika?.();
    setOpen(false);
  }

  if (!open) return null;
  return (
    <div className="cookie-bar" role="dialog" aria-label="Cookie">
      <p>
        Мы используем cookie и Яндекс Метрику, чтобы понимать, как работает сайт и реклама.{" "}
        <a href="/legal#cookies">Подробнее</a>
      </p>
      <div className="cookie-actions">
        <button className="btn gold" type="button" onClick={() => choose("all")}>Принять</button>
        <button className="btn ghost" type="button" onClick={() => choose("needed")}>Только необходимые</button>
      </div>
    </div>
  );
}

export function ConsentBoxes({
  priv,
  mkt,
  setPriv,
  setMkt,
}: {
  priv: boolean;
  mkt: boolean;
  setPriv: (value: boolean) => void;
  setMkt: (value: boolean) => void;
}) {
  return (
    <>
      <label className={`chk ${priv ? "on" : ""}`} onClick={() => setPriv(!priv)}>
        <i />
        <span>
          Даю <a href="/legal#consent" onClick={(e) => e.stopPropagation()}>согласие на обработку персональных данных</a>
          {" "}и принимаю <a href="/legal#offer" onClick={(e) => e.stopPropagation()}>оферту</a>
        </span>
      </label>
      <label className={`chk ${mkt ? "on" : ""}`} onClick={() => setMkt(!mkt)}>
        <i />
        <span>
          Согласна получать разборы и предложения на почту (<a href="/legal#mailing" onClick={(e) => e.stopPropagation()}>условия рассылки</a>). Отписаться можно в любом письме
        </span>
      </label>
    </>
  );
}
