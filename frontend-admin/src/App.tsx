import React, { useEffect, useState } from "react";
import { api, BillingData, BillingUsageRow, LogRow, MemoryRow, MessageRow, PaymentRow, PersonRow, ReadingRow, ReferralRow, RequestLogRow, TarotCardRow, UserDetail, UserRow, WithdrawalRow } from "./api";

type Route =
  | { page: "dashboard" }
  | { page: "tokens" }
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
  if (parts[0] === "logs") return { page: "logs" };
  if (parts[0] === "billing") return { page: "billing" };
  if (parts[0] === "referrals") return { page: "referrals" };
  if (parts[0] === "tarot") return { page: "tarot" };
  return { page: "dashboard" };
}

function navigate(route: Route) {
  if (route.page === "dashboard") window.location.hash = "/";
  else if (route.page === "user") window.location.hash = `/users/${route.id}`;
  else if (route.page === "tokens") window.location.hash = "/tokens";
  else window.location.hash = `/${route.page}`;
}

export function App() {
  const [route, setRoute] = useState<Route>(parseRoute());

  useEffect(() => {
    const onHash = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">AI Tarot Admin</div>
        <nav>
          <NavItem active={route.page === "dashboard"} onClick={() => navigate({ page: "dashboard" })}>Статистика</NavItem>
          <NavItem active={route.page === "tokens"} onClick={() => navigate({ page: "tokens" })}>Токены</NavItem>
          <NavItem active={route.page === "users" || route.page === "user"} onClick={() => navigate({ page: "users" })}>Пользователи</NavItem>
          <NavItem active={route.page === "logs"} onClick={() => navigate({ page: "logs" })}>Логи</NavItem>
          <NavItem active={route.page === "billing"} onClick={() => navigate({ page: "billing" })}>Биллинг</NavItem>
          <NavItem active={route.page === "referrals"} onClick={() => navigate({ page: "referrals" })}>Рефералка</NavItem>
          <NavItem active={route.page === "tarot"} onClick={() => navigate({ page: "tarot" })}>Карты Таро</NavItem>
        </nav>
      </aside>
      <main className="content">
        {route.page === "dashboard" && <DashboardPage />}
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
  const [stats, setStats] = useState<Record<string, number | string> | null>(null);
  const [signups, setSignups] = useState<{ date: string; count: number }[]>([]);

  useEffect(() => {
    api.dashboard().then(setStats);
    api.signups(30).then(setSignups);
  }, []);

  const maxSignup = Math.max(...signups.map((s) => s.count), 1);

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

  const reloadUserData = () => {
    api.user(id).then(setUser);
    api.userBilling(id).then(setBilling);
  };

  useEffect(() => {
    api.user(id).then(setUser);
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
          <thead><tr><th>Реферер</th><th>%</th><th>Начислено</th></tr></thead>
          <tbody>
            {refs.map((r) => (
              <tr key={r.id}><td>{r.referrer_name}</td><td>{r.reward_percent}%</td><td>{r.accrued_rub} ₽</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <h2>Заявки на вывод</h2>
        <table>
          <thead><tr><th>Пользователь</th><th>Сумма</th><th>Статус</th><th>Реквизиты</th><th></th></tr></thead>
          <tbody>
            {withdrawals.map((w) => (
              <tr key={w.id}>
                <td>{w.user_name ?? w.telegram_id}</td>
                <td>{w.amount_rub} ₽</td>
                <td><span className={`badge ${w.status === "pending" ? "yellow" : w.status === "approved" ? "green" : "gray"}`}>{w.status}</span></td>
                <td><code>{JSON.stringify(w.payout_details)}</code></td>
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

function Metric({ title, value }: { title: string; value: number | string }) {
  return <article className="metric"><span>{title}</span><strong>{value}</strong></article>;
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
