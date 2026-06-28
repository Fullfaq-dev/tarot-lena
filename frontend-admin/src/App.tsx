import React, { useEffect, useState } from "react";
import { api, getToken, login, setToken, BillingData, BillingUsageRow, DashboardStats, LandingStats, LogRow, MemoryRow, MessageRow, PaymentRow, PersonRow, ReadingRow, ReferralRow, RequestLogRow, TarotCardRow, UserDetail, UserRow, WithdrawalRow } from "./api";

type Route =
  | { page: "dashboard" }
  | { page: "tokens" }
  | { page: "landing" }
  | { page: "users" }
  | { page: "user"; id: string }
  | { page: "logs" }
  | { page: "billing" }
  | { page: "referrals" }
  | { page: "tarot" };

function parseRoute(): Route {
  const hash = window.location.hash.replace("#", "") || "/";
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "users" && parts[1]) return { page: "user", id: parts[1] };
  if (parts[0] === "users") return { page: "users" };
  if (parts[0] === "tokens") return { page: "tokens" };
  if (parts[0] === "landing") return { page: "landing" };
  if (parts[0] === "logs") return { page: "logs" };
  if (parts[0] === "billing") return { page: "billing" };
  if (parts[0] === "referrals") return { page: "referrals" };
  if (parts[0] === "tarot") return { page: "tarot" };
  return { page: "dashboard" };
}

function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await login(email.trim(), password);
      setToken(data.access_token);
      onSuccess();
    } catch {
      setError("Неверный логин или пароль");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <h1>Arcana AI Panel</h1>
        <p className="muted">Вход в панель управления</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" />
        </label>
        <label>
          Пароль
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>{loading ? "Вход…" : "Войти"}</button>
      </form>
    </div>
  );
}

function navigate(route: Route) {
  if (route.page === "dashboard") window.location.hash = "/";
  else if (route.page === "user") window.location.hash = `/users/${route.id}`;
  else if (route.page === "tokens") window.location.hash = "/tokens";
  else window.location.hash = `/${route.page}`;
}

export function App() {
  const [authed, setAuthed] = useState(Boolean(getToken()));
  const [route, setRoute] = useState<Route>(parseRoute());

  useEffect(() => {
    const onHash = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (!authed) {
    return <LoginPage onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">Arcana AI Panel</div>
        <nav>
          <NavItem active={route.page === "dashboard"} onClick={() => navigate({ page: "dashboard" })}>Статистика</NavItem>
          <NavItem active={route.page === "landing"} onClick={() => navigate({ page: "landing" })}>Лендинг</NavItem>
          <NavItem active={route.page === "tokens"} onClick={() => navigate({ page: "tokens" })}>Токены</NavItem>
          <NavItem active={route.page === "users" || route.page === "user"} onClick={() => navigate({ page: "users" })}>Пользователи</NavItem>
          <NavItem active={route.page === "logs"} onClick={() => navigate({ page: "logs" })}>Логи</NavItem>
          <NavItem active={route.page === "billing"} onClick={() => navigate({ page: "billing" })}>Биллинг</NavItem>
          <NavItem active={route.page === "referrals"} onClick={() => navigate({ page: "referrals" })}>Рефералка</NavItem>
          <NavItem active={route.page === "tarot"} onClick={() => navigate({ page: "tarot" })}>Карты Таро</NavItem>
        </nav>
        <button className="logout-btn" type="button" onClick={() => { setToken(null); setAuthed(false); }}>
          Выйти
        </button>
      </aside>
      <main className="content">
        {route.page === "dashboard" && <DashboardPage />}
        {route.page === "landing" && <LandingPage />}
        {route.page === "tokens" && <TokensPage />}
        {route.page === "users" && <UsersPage />}
        {route.page === "user" && <UserDetailPage id={route.id} />}
        {route.page === "logs" && <LogsPage />}
        {route.page === "billing" && <BillingPage />}
        {route.page === "referrals" && <ReferralsPage />}
        {route.page === "tarot" && <TarotPage />}
      </main>
    </div>
  );
}

function NavItem({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick}>{children}</button>;
}

function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [signups, setSignups] = useState<{ date: string; count: number }[]>([]);

  useEffect(() => {
    api.dashboard().then(setStats);
    api.signups(30).then(setSignups);
  }, []);

  const maxSignup = Math.max(...signups.map((s) => s.count), 1);
  const plategaBalances = stats?.platega_balances ?? [];

  const formatPlategaAmount = (value: number, currency: string) => {
    const formatted = value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
    if (currency === "RUB") return `${formatted} ₽`;
    return `${formatted} ${currency}`;
  };

  return (
    <>
      <h1>Статистика</h1>
      <div className="cards grid-4">
        <Metric title="Всего пользователей" value={Number(stats?.users ?? 0)} />
        <Metric title="DAU" value={Number(stats?.dau ?? 0)} />
        <Metric title="WAU" value={Number(stats?.wau ?? 0)} />
        <Metric title="MAU" value={Number(stats?.mau ?? 0)} />
        <Metric title="Активные (7д)" value={Number(stats?.active_users ?? 0)} />
        <Metric title="Неактивные" value={Number(stats?.inactive_users ?? 0)} />
        <Metric title="Расклады" value={Number(stats?.readings ?? 0)} />
        <Metric title="Платежи" value={Number(stats?.payments_count ?? 0)} />
        <Metric title="Сумма платежей" value={`${stats?.payments_total_rub ?? 0} ₽`} />
        <Metric title="Plus" value={Number(stats?.plus_subscribers ?? 0)} />
        <Metric title="Premium" value={Number(stats?.premium_subscribers ?? 0)} />
        <Metric title="Заявки на вывод" value={Number(stats?.pending_withdrawals ?? 0)} />
      </div>

      <section className="panel">
        <h2>Балансы Platega</h2>
        {stats?.platega_balances_error && (
          <p className="error">{stats.platega_balances_error}</p>
        )}
        {plategaBalances.length > 0 ? (
          <div className="cards grid-4">
            {plategaBalances.map((balance) => (
              <Metric
                key={balance.currency}
                title={balance.currency}
                value={formatPlategaAmount(balance.amount, balance.currency)}
                hint={
                  balance.frozen_balance > 0
                    ? `Заморожено: ${formatPlategaAmount(balance.frozen_balance, balance.currency)}`
                    : undefined
                }
              />
            ))}
          </div>
        ) : (
          !stats?.platega_balances_error && <p className="muted">Нет данных по балансам</p>
        )}
      </section>

      <section className="panel">
        <h2>Новые пользователи за 30 дней</h2>
        <div className="chart">
          {signups.map((s) => (
            <div key={s.date} className="chart-bar-wrap" title={`${s.date}: ${s.count}`}>
              <div className="chart-bar" style={{ height: `${(s.count / maxSignup) * 100}%` }} />
              <span className="chart-label">{s.date.slice(5)}</span>
            </div>
          ))}
          {signups.length === 0 && <p className="muted">Пока нет данных</p>}
        </div>
      </section>
    </>
  );
}

function LandingPage() {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState<LandingStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.landingStats(days)
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить статистику"))
      .finally(() => setLoading(false));
  }, [days]);

  const maxDaily = Math.max(...(stats?.daily.map((d) => d.sessions) ?? [1]), 1);

  const formatDuration = (sec: number | null | undefined) => {
    if (!sec) return "—";
    if (sec < 60) return `${sec} сек`;
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return s ? `${m} мин ${s} сек` : `${m} мин`;
  };

  const sectionLabel = (id: string) => ({
    hero: "Главный экран",
    features: "Возможности",
    referral: "Реферальная программа",
    how: "Как начать",
    "wide-cta": "Финальный CTA",
    header: "Шапка",
  }[id] ?? id);

  return (
    <>
      <h1>Аналитика лендинга</h1>
      <div className="toolbar">
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>7 дней</option>
          <option value={30}>30 дней</option>
          <option value={90}>90 дней</option>
        </select>
      </div>

      {loading && <p className="muted">Загрузка…</p>}
      {error && <p className="error">{error}</p>}

      {stats && (
        <>
          <div className="cards grid-4">
            <Metric title="Визиты (сессии)" value={stats.summary.sessions} />
            <Metric title="Уникальные посетители" value={stats.summary.unique_visitors} />
            <Metric title="Среднее время на сайте" value={formatDuration(stats.summary.avg_duration_sec)} />
            <Metric title="Средняя глубина скролла" value={`${stats.summary.avg_scroll_pct}%`} />
            <Metric title="Всего кликов" value={stats.summary.total_clicks} />
            <Metric title="Клики в Telegram" value={stats.summary.cta_clicks} />
            <Metric title="Переходы в бота (start=landing)" value={stats.summary.bot_conversions} />
            <Metric title="Конверсия в бота" value={`${stats.summary.conversion_rate_pct}%`} hint="Сессии → /start landing" />
          </div>

          <section className="panel">
            <h2>Посещения по дням</h2>
            <div className="chart">
              {stats.daily.map((d) => (
                <div key={d.date} className="chart-bar-wrap" title={`${d.date}: ${d.sessions} визитов`}>
                  <div className="chart-bar" style={{ height: `${(d.sessions / maxDaily) * 100}%` }} />
                  <span className="chart-label">{d.date.slice(5)}</span>
                </div>
              ))}
              {stats.daily.length === 0 && <p className="muted">Пока нет данных — трекинг начнёт собирать статистику после деплоя</p>}
            </div>
          </section>

          <div className="grid-2">
            <section className="panel">
              <h2>Топ кликов</h2>
              <table>
                <thead>
                  <tr><th>Элемент</th><th>Секция</th><th>Кликов</th></tr>
                </thead>
                <tbody>
                  {stats.top_clicks.map((row, i) => (
                    <tr key={`${row.label}-${i}`}>
                      <td>{row.label}</td>
                      <td>{row.section ? sectionLabel(row.section) : "—"}</td>
                      <td>{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {stats.top_clicks.length === 0 && <p className="muted">Кликов пока нет</p>}
            </section>

            <section className="panel">
              <h2>Просмотры секций</h2>
              <table>
                <thead>
                  <tr><th>Секция</th><th>Просмотров</th></tr>
                </thead>
                <tbody>
                  {stats.top_sections.map((row) => (
                    <tr key={row.section_id}>
                      <td>{sectionLabel(row.section_id)}</td>
                      <td>{row.views}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {stats.top_sections.length === 0 && <p className="muted">Просмотров секций пока нет</p>}
            </section>
          </div>

          <div className="grid-2">
            <section className="panel">
              <h2>Устройства</h2>
              <table>
                <thead><tr><th>Тип</th><th>Сессии</th></tr></thead>
                <tbody>
                  {stats.devices.map((row) => (
                    <tr key={row.device}><td>{row.device}</td><td>{row.sessions}</td></tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className="panel">
              <h2>UTM source</h2>
              <table>
                <thead><tr><th>Источник</th><th>Сессии</th></tr></thead>
                <tbody>
                  {stats.utm_sources.map((row) => (
                    <tr key={row.source}><td>{row.source}</td><td>{row.sessions}</td></tr>
                  ))}
                </tbody>
              </table>
              {stats.utm_sources.length === 0 && <p className="muted">UTM-меток пока нет</p>}
            </section>
          </div>

          <section className="panel">
            <h2>Последние визиты</h2>
            <table>
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Устройство</th>
                  <th>Время на сайте</th>
                  <th>Скролл</th>
                  <th>Клики</th>
                  <th>UTM</th>
                  <th>Referrer</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_sessions.map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString("ru")}</td>
                    <td>{row.device_type ?? "—"}</td>
                    <td>{formatDuration(row.duration_sec)}</td>
                    <td>{row.max_scroll_pct}%</td>
                    <td>{row.click_count}</td>
                    <td>{row.utm_source ?? "—"}</td>
                    <td className="muted">{row.referrer ? row.referrer.slice(0, 60) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {stats.recent_sessions.length === 0 && <p className="muted">Визитов пока нет</p>}
          </section>
        </>
      )}
    </>
  );
}

function TokensPage() {
  const [days, setDays] = useState(30);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [stats, setStats] = useState<Awaited<ReturnType<typeof api.tokenStats>> | null>(null);

  const load = () => {
    api.tokenStats(days, dateFrom || undefined, dateTo || undefined).then(setStats);
  };

  useEffect(() => { load(); }, [days]);

  const maxTokens = Math.max(...(stats?.daily.map((d) => d.total_tokens) ?? [1]), 1);

  return (
    <>
      <h1>Статистика токенов</h1>
      <div className="toolbar">
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>7 дней</option>
          <option value={30}>30 дней</option>
          <option value={90}>90 дней</option>
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <button onClick={load}>Применить</button>
      </div>

      {stats && (
        <>
          <div className="cards grid-4">
            <Metric title="Всего токенов" value={stats.summary.total_tokens} />
            <Metric title="Входящие" value={stats.summary.input_tokens} />
            <Metric title="Исходящие" value={stats.summary.output_tokens} />
            <Metric title="Запросов" value={stats.summary.requests} />
            <Metric title="KIE credits" value={stats.summary.kie_credits} />
            <Metric title="Себестоимость" value={`$${stats.summary.provider_cost_usd}`} />
            <Metric title="Себестоимость ₽" value={`${stats.summary.provider_cost_rub} ₽`} />
            <Metric title="Списано с пользователей" value={`${stats.summary.charged_rub} ₽`} />
            <Metric title="Маржа" value={`${stats.summary.margin_rub} ₽`} />
          </div>

          {stats.summary.pricing_note && (
            <p className="muted">{stats.summary.pricing_note}</p>
          )}

          <section className="panel">
            <h2>По дням</h2>
            <div className="chart">
              {stats.daily.map((d) => (
                <div key={d.date} className="chart-bar-wrap" title={`${d.date}: ${d.total_tokens} ток.`}>
                  <div className="chart-bar" style={{ height: `${(d.total_tokens / maxTokens) * 100}%` }} />
                  <span className="chart-label">{d.date.slice(5)}</span>
                </div>
              ))}
              {stats.daily.length === 0 && <p className="muted">Пока нет данных</p>}
            </div>
            <table>
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Вход</th>
                  <th>Выход</th>
                  <th>Всего</th>
                  <th>Себестоимость</th>
                  <th>Списано</th>
                  <th>Запросов</th>
                </tr>
              </thead>
              <tbody>
                {stats.daily.map((d) => (
                  <tr key={d.date}>
                    <td>{d.date}</td>
                    <td>{d.input_tokens}</td>
                    <td>{d.output_tokens}</td>
                    <td>{d.total_tokens}</td>
                    <td>${d.provider_cost_usd}</td>
                    <td>{d.charged_rub} ₽</td>
                    <td>{d.requests}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}

function UsersPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [filter, setFilter] = useState<"all" | "active" | "inactive">("all");

  useEffect(() => { api.users().then(setUsers); }, []);

  const filtered = users.filter((u) => {
    if (filter === "active") return u.is_active;
    if (filter === "inactive") return !u.is_active;
    return true;
  });

  return (
    <>
      <h1>Пользователи</h1>
      <div className="toolbar">
        <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}>
          <option value="all">Все</option>
          <option value="active">Активные</option>
          <option value="inactive">Неактивные</option>
        </select>
      </div>
      <section className="panel">
        <table>
          <thead>
            <tr>
              <th>Статус</th>
              <th>Имя</th>
              <th>Telegram</th>
              <th>Тариф</th>
              <th>Сообщений</th>
              <th>Баланс</th>
              <th>Последняя активность</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id} className="clickable" onClick={() => navigate({ page: "user", id: u.id })}>
                <td><span className={`badge ${u.is_active ? "green" : "gray"}`}>{u.is_active ? "активен" : "неактивен"}</span></td>
                <td>{u.first_name ?? "—"}</td>
                <td>@{u.username ?? u.telegram_id}</td>
                <td>{u.tier}</td>
                <td>{u.message_count}</td>
                <td>{u.balance_rub} ₽</td>
                <td>{u.last_active_at ? new Date(u.last_active_at).toLocaleString("ru") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function UserDetailPage({ id }: { id: string }) {
  const [user, setUser] = useState<UserDetail | null>(null);
  const [tab, setTab] = useState("profile");
  const [messages, setMessages] = useState<MessageRow[]>([]);
  const [memories, setMemories] = useState<MemoryRow[]>([]);
  const [people, setPeople] = useState<PersonRow[]>([]);
  const [readings, setReadings] = useState<ReadingRow[]>([]);
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [topupAmount, setTopupAmount] = useState("100");
  const [topupComment, setTopupComment] = useState("");
  const [topupStatus, setTopupStatus] = useState<string | null>(null);
  const [topupLoading, setTopupLoading] = useState(false);
  const [referralPercent, setReferralPercent] = useState("40");
  const [referralStatus, setReferralStatus] = useState<string | null>(null);
  const [referralLoading, setReferralLoading] = useState(false);

  const reloadUserData = () => {
    api.user(id).then((data) => {
      setUser(data);
      setReferralPercent(String(data.referral_reward_percent ?? 40));
    });
    api.userBilling(id).then(setBilling);
  };

  useEffect(() => {
    api.user(id).then((data) => {
      setUser(data);
      setReferralPercent(String(data.referral_reward_percent ?? 40));
    });
    api.userMessages(id).then(setMessages);
    api.userMemories(id).then(setMemories);
    api.userPeople(id).then(setPeople);
    api.userReadings(id).then(setReadings);
    api.userBilling(id).then(setBilling);
  }, [id]);

  const handleTopup = async () => {
    const amount = topupAmount.replace(",", ".").trim();
    if (!amount || Number(amount) <= 0) {
      setTopupStatus("Укажи сумму больше нуля");
      return;
    }
    setTopupLoading(true);
    setTopupStatus(null);
    try {
      const result = await api.topupUserBalance(id, amount, topupComment);
      setTopupStatus(`Пополнено на ${result.amount_rub} ₽. Новый баланс: ${result.balance_rub} ₽`);
      setTopupComment("");
      reloadUserData();
    } catch (err) {
      setTopupStatus(err instanceof Error ? err.message : "Не удалось пополнить баланс");
    } finally {
      setTopupLoading(false);
    }
  };

  const handleReferralPercent = async () => {
    const percent = Number(referralPercent);
    if (!Number.isInteger(percent) || percent < 1 || percent > 100) {
      setReferralStatus("Укажи процент от 1 до 100");
      return;
    }
    setReferralLoading(true);
    setReferralStatus(null);
    try {
      const result = await api.updateReferralPercent(id, percent);
      setReferralStatus(`Реферальный процент обновлён: ${result.referral_reward_percent}%`);
      reloadUserData();
    } catch (err) {
      setReferralStatus(err instanceof Error ? err.message : "Не удалось обновить процент");
    } finally {
      setReferralLoading(false);
    }
  };

  if (!user) return <p>Загрузка...</p>;

  const tabs = ["profile", "chat", "memories", "people", "readings", "billing"] as const;

  return (
    <>
      <button className="back" onClick={() => navigate({ page: "users" })}>← Назад</button>
      <h1>{user.first_name ?? "Пользователь"} <span className={`badge ${user.is_active ? "green" : "gray"}`}>{user.is_active ? "активен" : "неактивен"}</span></h1>
      <div className="tabs">
        {tabs.map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "profile" && "Профиль"}
            {t === "chat" && "Переписка"}
            {t === "memories" && "Память"}
            {t === "people" && "Люди"}
            {t === "readings" && "Расклады"}
            {t === "billing" && "Биллинг"}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <section className="panel grid-2">
          <div>
            <h3>Основное</h3>
            <p>Telegram ID: {user.telegram_id}</p>
            <p>Username: @{user.username ?? "—"}</p>
            <p>Тариф: {user.tier}</p>
            <p>Баланс: {user.balance_rub} ₽</p>
            <p>Анкета: {user.is_onboarded ? "завершена" : "в процессе"}</p>
            <p>Регистрация: {new Date(user.created_at).toLocaleString("ru")}</p>
            <h3>Реферальная программа</h3>
            <p>Текущий партнёрский процент: <strong>{user.referral_reward_percent ?? 40}%</strong></p>
            <div className="toolbar">
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                value={referralPercent}
                onChange={(e) => setReferralPercent(e.target.value)}
                placeholder="Процент"
              />
              <button onClick={handleReferralPercent} disabled={referralLoading}>
                {referralLoading ? "Сохраняем…" : "Сохранить %"}
              </button>
            </div>
            {referralStatus && <p className="muted">{referralStatus}</p>}
          </div>
          <div>
            <h3>Онбординг</h3>
            {user.onboarding ? (
              <ul className="kv-list">
                {Object.entries(user.onboarding.answers).map(([k, v]) => (
                  <li key={k}><strong>{k}:</strong> {v}</li>
                ))}
              </ul>
            ) : <p className="muted">Нет данных</p>}
            {user.soul_profile && (
              <>
                <h3>Soul Profile</h3>
                <ul className="kv-list">
                  {Object.entries(user.soul_profile).filter(([, v]) => v).map(([k, v]) => (
                    <li key={k}><strong>{k}:</strong> {typeof v === "object" ? JSON.stringify(v) : String(v)}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </section>
      )}

      {tab === "chat" && (
        <section className="panel chat-log">
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.role}`}>
              <div className="chat-meta">
                {m.role} · {new Date(m.created_at).toLocaleString("ru")}
                {m.role === "user" && m.tokens_input > 0 && (
                  <span> · вопрос: {m.tokens_input} ток.</span>
                )}
                {m.role === "assistant" && (m.tokens_input > 0 || m.tokens_output > 0) && (
                  <span>
                    {" "}· вх: {m.tokens_input} исх: {m.tokens_output} ток.
                    {m.cost_rub !== "0" && ` · списано ${m.cost_rub} ₽`}
                    {m.meta?.provider_cost_usd && Number(m.meta.provider_cost_usd) > 0 && (
                      <span>
                        {` · себест. $${m.meta.provider_cost_usd}`}
                        {m.meta?.provider_cost_rub ? ` (${m.meta.provider_cost_rub} ₽)` : ""}
                      </span>
                    )}
                    {m.meta?.model && ` · ${String(m.meta.model)}`}
                  </span>
                )}
              </div>
              <div>{m.content}</div>
              {m.meta?.source_image_url && (
                <div className="vision-links">
                  <a href={String(m.meta.source_image_url)} target="_blank" rel="noreferrer">
                    <img
                      src={String(m.meta.source_image_url)}
                      alt="Фото пользователя"
                      style={{ maxWidth: 140, borderRadius: 8, display: "block", marginBottom: 6 }}
                    />
                    📷 Открыть фото
                  </a>
                </div>
              )}
              {Array.isArray(m.meta?.infographic_urls) && m.meta.infographic_urls.length > 0 && (
                <div className="vision-links">
                  {(m.meta.infographic_urls as string[]).map((url, idx) => (
                    <a key={url} href={url} target="_blank" rel="noreferrer">
                      🖼 Инфографика {idx + 1}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {tab === "memories" && (
        <section className="panel">
          {memories.map((m) => (
            <article key={m.id} className="memory-card">
              <span className="badge">{m.type}</span>
              <span className="importance">важность {m.importance}</span>
              <p>{m.description}</p>
              <small>{new Date(m.created_at).toLocaleString("ru")}</small>
            </article>
          ))}
          {memories.length === 0 && <p className="muted">Память пока пуста</p>}
        </section>
      )}

      {tab === "people" && (
        <section className="panel">
          <table>
            <thead><tr><th>Имя</th><th>Тип</th><th>Заметки</th></tr></thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}><td>{p.display_name}</td><td>{p.relationship_type}</td><td>{p.notes ?? "—"}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === "readings" && (
        <section className="panel">
          {readings.map((r) => (
            <article key={r.id} className="reading-card">
              <h4>{r.reading_type}</h4>
              <p><strong>Вопрос:</strong> {r.question}</p>
              <p>{r.interpretation}</p>
              <small>{new Date(r.created_at).toLocaleString("ru")}</small>
            </article>
          ))}
        </section>
      )}

      {tab === "billing" && billing && (
        <section className="panel">
          <h3>Пополнить баланс вручную</h3>
          <div className="toolbar">
            <input
              type="number"
              min="1"
              step="1"
              value={topupAmount}
              onChange={(e) => setTopupAmount(e.target.value)}
              placeholder="Сумма, ₽"
            />
            <input
              type="text"
              value={topupComment}
              onChange={(e) => setTopupComment(e.target.value)}
              placeholder="Комментарий (необязательно)"
            />
            <button onClick={handleTopup} disabled={topupLoading}>
              {topupLoading ? "Пополняем…" : "Пополнить"}
            </button>
          </div>
          {topupStatus && <p className="muted">{topupStatus}</p>}

          <h3>Платежи и пополнения</h3>
          <PaymentsTable rows={billing.payments} />

          <h3>AI-запросы и списания</h3>
          <UsageTable rows={billing.usage} />
        </section>
      )}
    </>
  );
}

function LogsPage() {
  const [botLogs, setBotLogs] = useState<LogRow[]>([]);
  const [reqLogs, setReqLogs] = useState<RequestLogRow[]>([]);
  const [tab, setTab] = useState<"bot" | "requests">("bot");

  useEffect(() => {
    api.botLogs().then(setBotLogs);
    api.requestLogs().then(setReqLogs);
  }, []);

  return (
    <>
      <h1>Логи</h1>
      <div className="tabs">
        <button className={tab === "bot" ? "active" : ""} onClick={() => setTab("bot")}>Бот</button>
        <button className={tab === "requests" ? "active" : ""} onClick={() => setTab("requests")}>AI-запросы</button>
      </div>
      <section className="panel log-table">
        {tab === "bot" && botLogs.map((l, i) => (
          <div key={i} className="log-row">
            <span className="log-time">{l.created_at ? new Date(l.created_at).toLocaleString("ru") : ""}</span>
            <span className="badge">{l.event_name}</span>
            <span className="muted">{l.user_id ?? "—"}</span>
            <code>{JSON.stringify(l.payload)}</code>
          </div>
        ))}
        {tab === "requests" && reqLogs.map((l) => (
          <div key={l.id} className="log-row">
            <span className="log-time">{new Date(l.created_at).toLocaleString("ru")}</span>
            <span className="badge">{l.feature}</span>
            <span>{l.model}</span>
            <span>in:{l.input_units} out:{l.output_units}</span>
            <span>{l.kie_credits ? `${l.kie_credits} cr` : `$${l.provider_cost_usd}`}</span>
            <span>{l.charged_rub} ₽</span>
          </div>
        ))}
      </section>
    </>
  );
}

function BillingPage() {
  const [payments, setPayments] = useState<PaymentRow[]>([]);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [actionStatus, setActionStatus] = useState("");

  const reload = () => {
    api.payments().then(setPayments);
    api.users().then(setUsers);
  };

  useEffect(() => {
    reload();
  }, []);

  const approve = async (id: string) => {
    setActionStatus("");
    try {
      await api.approvePayment(id);
      reload();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Не удалось провести платёж");
    }
  };

  const reject = async (id: string) => {
    setActionStatus("");
    try {
      await api.rejectPayment(id);
      reload();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Не удалось отклонить платёж");
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm("Удалить инвойс?")) return;
    setActionStatus("");
    try {
      await api.deletePayment(id);
      reload();
    } catch (e) {
      setActionStatus(e instanceof Error ? e.message : "Не удалось удалить платёж");
    }
  };

  const pendingCount = payments.filter((p) => p.status === "pending").length;

  return (
    <>
      <h1>Биллинг</h1>
      <section className="panel">
        <h2>Балансы пользователей</h2>
        <table>
          <thead><tr><th>Имя</th><th>Тариф</th><th>Баланс</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="clickable" onClick={() => navigate({ page: "user", id: u.id })}>
                <td>{u.first_name ?? u.telegram_id}</td>
                <td>{u.tier}</td>
                <td>{u.balance_rub} ₽</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Инвойсы {pendingCount > 0 && <span className="badge yellow">{pendingCount} ожидают</span>}</h2>
        {actionStatus && <p className="muted">{actionStatus}</p>}
        <table>
          <thead>
            <tr>
              <th>Пользователь</th>
              <th>Назначение</th>
              <th>Провайдер</th>
              <th>Статус</th>
              <th>Сумма</th>
              <th>Дата</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td
                  className="clickable"
                  onClick={() => navigate({ page: "user", id: p.user_id })}
                >
                  {p.user_name ?? p.telegram_id}
                </td>
                <td>{p.purpose_label}</td>
                <td>{p.provider}</td>
                <td>
                  <span className={`badge ${
                    p.status === "pending" ? "yellow" : p.status === "completed" ? "green" : "gray"
                  }`}>
                    {p.status_label}
                  </span>
                  {p.admin_comment && <div className="muted">{p.admin_comment}</div>}
                </td>
                <td>{p.amount_rub} ₽</td>
                <td>{new Date(p.created_at).toLocaleString("ru")}</td>
                <td className="actions-cell">
                  {p.status === "pending" && (
                    <>
                      <button className="btn-sm" onClick={() => approve(p.id)}>Провести</button>
                      <button className="btn-sm danger" onClick={() => reject(p.id)}>Отклонить</button>
                    </>
                  )}
                  {p.status !== "completed" && (
                    <button className="btn-sm danger" onClick={() => remove(p.id)}>Удалить</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {payments.length === 0 && <p className="muted">Пока нет инвойсов</p>}
      </section>
    </>
  );
}

function ReferralsPage() {
  const [refs, setRefs] = useState<ReferralRow[]>([]);
  const [withdrawals, setWithdrawals] = useState<WithdrawalRow[]>([]);

  const reload = () => {
    api.referrals().then(setRefs);
    api.withdrawals().then(setWithdrawals);
  };

  useEffect(() => { reload(); }, []);

  const approve = async (id: string) => {
    await api.updateWithdrawal(id, "approved");
    reload();
  };

  const reject = async (id: string) => {
    await api.updateWithdrawal(id, "rejected", "Отклонено админом");
    reload();
  };

  return (
    <>
      <h1>Реферальная система</h1>
      <section className="panel">
        <h2>Рефералы</h2>
        <table>
          <thead>
            <tr>
              <th>Реферер</th>
              <th>Telegram ID</th>
              <th>Партнёр %</th>
              <th>% связи</th>
              <th>Начислено</th>
            </tr>
          </thead>
          <tbody>
            {refs.map((r) => (
              <tr key={r.id} className="clickable" onClick={() => navigate({ page: "user", id: r.referrer_user_id })}>
                <td>{r.referrer_name}</td>
                <td>{r.referrer_telegram_id}</td>
                <td>{r.partner_reward_percent}%</td>
                <td>{r.reward_percent}%</td>
                <td>{r.accrued_rub} ₽</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Заявки на вывод</h2>
        <table>
          <thead><tr><th>Пользователь</th><th>Сумма</th><th>Статус</th><th>Кошелёк USDT (TRC-20)</th><th>Дата</th><th></th></tr></thead>
          <tbody>
            {withdrawals.map((w) => (
              <tr key={w.id}>
                <td>{w.user_name ?? w.telegram_id}</td>
                <td>{w.amount_rub} ₽</td>
                <td><span className={`badge ${w.status === "pending" ? "yellow" : w.status === "approved" ? "green" : "gray"}`}>{w.status}</span></td>
                <td>
                  {typeof w.payout_details?.usdt_trc20 === "string"
                    ? <code>{w.payout_details.usdt_trc20 as string}</code>
                    : <code>{JSON.stringify(w.payout_details)}</code>}
                </td>
                <td>{new Date(w.created_at).toLocaleDateString("ru-RU")}</td>
                <td>
                  {w.status === "pending" && (
                    <>
                      <button className="btn-sm" onClick={() => approve(w.id)}>Одобрить</button>
                      <button className="btn-sm danger" onClick={() => reject(w.id)}>Отклонить</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function TarotPage() {
  const [cards, setCards] = useState<TarotCardRow[]>([]);
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [number, setNumber] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  const reload = () => api.tarotCards().then(setCards);
  useEffect(() => { reload(); }, []);

  const upload = async () => {
    if (!file || !slug || !name) return;
    const form = new FormData();
    form.append("slug", slug);
    form.append("name", name);
    form.append("number", String(number));
    form.append("file", file);
    await api.uploadTarotCard(form);
    setStatus("Карта загружена");
    reload();
  };

  return (
    <>
      <h1>Карты Таро</h1>
      <section className="panel">
        <h2>Загрузить обложку</h2>
        <div className="form-grid">
          <input placeholder="slug (fool)" value={slug} onChange={(e) => setSlug(e.target.value)} />
          <input placeholder="Название" value={name} onChange={(e) => setName(e.target.value)} />
          <input type="number" placeholder="Номер" value={number} onChange={(e) => setNumber(Number(e.target.value))} />
          <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button onClick={upload}>Загрузить</button>
        </div>
        {status && <p className="ok">{status}</p>}
      </section>
      <section className="panel cards-grid">
        {cards.map((c) => (
          <article key={c.id} className="tarot-card-preview">
            <img src={`/static/tarot_cards/${c.image_path.split("/").pop()}`} alt={c.name} onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            <div>{c.number}. {c.name}</div>
            <small>{c.slug}</small>
          </article>
        ))}
        {cards.length === 0 && <p className="muted">Карты ещё не загружены</p>}
      </section>
    </>
  );
}

function Metric({ title, value, hint }: { title: string; value: number | string; hint?: string }) {
  return (
    <article className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
      {hint && <small className="muted">{hint}</small>}
    </article>
  );
}

function MiniTable({ rows }: { rows: string[][] }) {
  return (
    <table className="mini">
      <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table>
  );
}

type UsageSortKey =
  | "created_at"
  | "feature_label"
  | "billing_mode_label"
  | "input_units"
  | "output_units"
  | "total_tokens"
  | "provider_cost_usd"
  | "provider_cost_rub"
  | "image_charged_rub"
  | "charged_rub";

function UsageTable({ rows }: { rows: BillingUsageRow[] }) {
  const [sortKey, setSortKey] = useState<UsageSortKey>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const toggleSort = (key: UsageSortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir(key === "created_at" ? "desc" : "asc");
  };

  const sorted = [...rows].sort((a, b) => {
    const dir = sortDir === "asc" ? 1 : -1;
    if (sortKey === "created_at") {
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir;
    }
    if (["input_units", "output_units", "total_tokens"].includes(sortKey)) {
      return (Number(a[sortKey]) - Number(b[sortKey])) * dir;
    }
    if (["provider_cost_usd", "provider_cost_rub", "image_charged_rub", "charged_rub"].includes(sortKey)) {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return (Number(av) - Number(bv)) * dir;
    }
    return String(a[sortKey]).localeCompare(String(b[sortKey]), "ru") * dir;
  });

  const th = (key: UsageSortKey, label: string) => (
    <th className="sortable" onClick={() => toggleSort(key)}>
      {label}{sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );

  if (rows.length === 0) {
    return <p className="muted">Пока нет AI-запросов</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          {th("created_at", "Дата")}
          {th("feature_label", "Тип")}
          {th("billing_mode_label", "Режим")}
          {th("input_units", "Вход")}
          {th("output_units", "Выход")}
          {th("total_tokens", "Всего")}
          {th("provider_cost_usd", "Себест. $")}
          {th("provider_cost_rub", "Себест. ₽")}
          {th("image_charged_rub", "Картинка ₽")}
          {th("charged_rub", "Списано")}
          <th>Фото</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((u) => (
          <tr key={u.id}>
            <td>{new Date(u.created_at).toLocaleString("ru")}</td>
            <td>{u.feature_label}</td>
            <td><span className={`badge ${u.billing_mode === "free" ? "gray" : "green"}`}>{u.billing_mode_label}</span></td>
            <td>{u.input_units}</td>
            <td>{u.output_units}</td>
            <td>{u.total_tokens}</td>
            <td>${u.provider_cost_usd}</td>
            <td>{u.provider_cost_rub} ₽</td>
            <td>{u.with_infographic ? `${u.image_charged_rub ?? "0"} ₽` : "—"}</td>
            <td>{u.charged_rub} ₽</td>
            <td className="vision-links-cell">
              {u.source_image_url && (
                <a href={u.source_image_url} target="_blank" rel="noreferrer">📷</a>
              )}
              {(u.infographic_urls ?? []).map((url, idx) => (
                <a key={url} href={url} target="_blank" rel="noreferrer">🖼{idx + 1}</a>
              ))}
              {!u.source_image_url && !(u.infographic_urls ?? []).length && "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type PaymentSortKey = "created_at" | "purpose" | "status" | "amount_rub";

function PaymentsTable({ rows }: { rows: BillingData["payments"] }) {
  const [sortKey, setSortKey] = useState<PaymentSortKey>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const toggleSort = (key: PaymentSortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir(key === "created_at" ? "desc" : "asc");
  };

  const sorted = [...rows].sort((a, b) => {
    const dir = sortDir === "asc" ? 1 : -1;
    if (sortKey === "created_at") {
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir;
    }
    if (sortKey === "amount_rub") {
      return (Number(a.amount_rub) - Number(b.amount_rub)) * dir;
    }
    return String(a[sortKey]).localeCompare(String(b[sortKey]), "ru") * dir;
  });

  const th = (key: PaymentSortKey, label: string) => (
    <th className="sortable" onClick={() => toggleSort(key)}>
      {label}{sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );

  if (rows.length === 0) {
    return <p className="muted">Пока нет платежей</p>;
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          {th("created_at", "Дата")}
          {th("purpose", "Назначение")}
          {th("status", "Статус")}
          {th("amount_rub", "Сумма")}
        </tr>
      </thead>
      <tbody>
        {sorted.map((p) => (
          <tr key={p.id}>
            <td>{new Date(p.created_at).toLocaleString("ru")}</td>
            <td>{p.purpose}</td>
            <td>{p.status}</td>
            <td>{p.amount_rub} ₽</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
