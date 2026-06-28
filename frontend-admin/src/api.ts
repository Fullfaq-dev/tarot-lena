const BASE = "/admin-api";
const TOKEN_KEY = "arcana_admin_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    setToken(null);
    window.location.reload();
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  return handleResponse<T>(res);
}

async function patch(path: string, params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}?${qs}`, { method: "PATCH", headers: authHeaders() });
  return handleResponse(res);
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

async function del(path: string) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE", headers: authHeaders() });
  return handleResponse(res);
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function login(email: string, password: string) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Неверный логин или пароль");
  return res.json() as Promise<{ access_token: string; email: string }>;
}

export type PlategaBalance = {
  amount: number;
  currency: string;
  frozen_balance: number;
};

export type DashboardStats = {
  users: number;
  onboarded_users: number;
  readings: number;
  payments_count: number;
  payments_total_rub: string;
  dau: number;
  wau: number;
  mau: number;
  active_users: number;
  inactive_users: number;
  plus_subscribers: number;
  premium_subscribers: number;
  pending_withdrawals: number;
  platega_balances?: PlategaBalance[];
  platega_balances_error?: string;
};

export const api = {
  dashboard: () => get<DashboardStats>("/dashboard"),
  signups: (days = 30) => get<{ date: string; count: number }[]>(`/stats/signups?days=${days}`),
  landingStats: (days = 30) => get<LandingStats>(`/stats/landing?days=${days}`),
  tokenStats: (days = 30, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams({ days: String(days) });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return get<TokenStatsResponse>(`/stats/tokens?${params}`);
  },
  users: () => get<UserRow[]>("/users"),
  user: (id: string) => get<UserDetail>(`/users/${id}`),
  userMessages: (id: string) => get<MessageRow[]>(`/users/${id}/messages`),
  userMemories: (id: string) => get<MemoryRow[]>(`/users/${id}/memories`),
  userPeople: (id: string) => get<PersonRow[]>(`/users/${id}/people`),
  userReadings: (id: string) => get<ReadingRow[]>(`/users/${id}/readings`),
  userBilling: (id: string) => get<BillingData>(`/users/${id}/billing`),
  topupUserBalance: (id: string, amount_rub: string, comment?: string) =>
    post<{ user_id: string; amount_rub: string; balance_rub: string }>(
      `/users/${id}/balance/topup`,
      { amount_rub, comment: comment ?? "" },
    ),
  updateReferralPercent: (id: string, referral_reward_percent: number) =>
    patchJson<{ user_id: string; telegram_id: number; referral_reward_percent: number }>(
      `/users/${id}/referral-percent`,
      { referral_reward_percent },
    ),
  botLogs: () => get<LogRow[]>("/logs/bot"),
  requestLogs: () => get<RequestLogRow[]>("/logs/requests"),
  payments: () => get<PaymentRow[]>("/billing/payments"),
  approvePayment: (id: string, comment?: string) =>
    patch(`/billing/payments/${id}`, { status: "completed", ...(comment ? { admin_comment: comment } : {}) }),
  rejectPayment: (id: string, comment?: string) =>
    patch(`/billing/payments/${id}`, {
      status: "rejected",
      admin_comment: comment ?? "Отклонено админом",
    }),
  deletePayment: (id: string) => del(`/billing/payments/${id}`),
  referrals: () => get<ReferralRow[]>("/referrals"),
  withdrawals: () => get<WithdrawalRow[]>("/referrals/withdrawals"),
  updateWithdrawal: (id: string, status: string, comment?: string) =>
    patch(`/referrals/withdrawals/${id}`, { status, ...(comment ? { admin_comment: comment } : {}) }),
  tarotCards: () => get<TarotCardRow[]>("/tarot-cards"),
  uploadTarotCard: async (form: FormData) => {
    const res = await fetch(`${BASE}/tarot-cards/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: form,
    });
    return handleResponse(res);
  },
};

export type UserRow = {
  id: string;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  is_onboarded: boolean;
  is_blocked: boolean;
  balance_rub: string;
  tier: string;
  message_count: number;
  last_active_at: string | null;
  is_active: boolean;
  created_at: string;
  referral_reward_percent?: number;
};

export type UserDetail = UserRow & {
  soul_profile: Record<string, unknown> | null;
  onboarding: { current_step: string; answers: Record<string, string>; completed_at: string | null } | null;
  free_messages_used_month: number;
  free_readings_used_month: number;
  subscription_status: string | null;
  subscription_expires_at: string | null;
};

export type MessageRow = {
  id: string;
  role: string;
  content: string;
  tokens_input: number;
  tokens_output: number;
  cost_rub: string;
  provider_cost_usd?: string | null;
  meta?: Record<string, unknown>;
  created_at: string;
};

export type MemoryRow = {
  id: string;
  type: string;
  importance: number;
  description: string;
  happened_at: string | null;
  is_active: boolean;
  created_at: string;
};

export type PersonRow = {
  id: string;
  display_name: string;
  relationship_type: string;
  notes: string | null;
  importance: number;
};

export type ReadingRow = {
  id: string;
  reading_type: string;
  question: string;
  interpretation: string;
  created_at: string;
};

export type BillingUsageRow = {
  id: string;
  feature: string;
  feature_label: string;
  billing_mode: string;
  billing_mode_label: string;
  model: string | null;
  input_units: number;
  output_units: number;
  total_tokens: number;
  provider_cost_usd: string;
  provider_cost_rub: string;
  kie_credits: string | null;
  charged_rub: string;
  with_infographic?: boolean;
  image_model?: string | null;
  image_provider_cost_usd?: string | null;
  image_provider_cost_rub?: string | null;
  image_charged_rub?: string | null;
  chat_charged_rub?: string | null;
  source_image_url?: string | null;
  infographic_urls?: string[];
  created_at: string;
};

export type BillingData = {
  payments: { id: string; purpose: string; status: string; amount_rub: string; created_at: string }[];
  usage: BillingUsageRow[];
};

export type LandingStats = {
  summary: {
    sessions: number;
    unique_visitors: number;
    avg_duration_sec: number;
    avg_scroll_pct: number;
    total_clicks: number;
    cta_clicks: number;
    bot_conversions: number;
    conversion_rate_pct: number;
  };
  daily: { date: string; sessions: number; unique_visitors: number }[];
  top_clicks: { label: string; element_id: string | null; section: string | null; count: number }[];
  top_sections: { section_id: string; views: number }[];
  devices: { device: string; sessions: number }[];
  utm_sources: { source: string; sessions: number }[];
  recent_sessions: {
    id: string;
    visitor_id: string;
    page: string;
    device_type: string | null;
    duration_sec: number | null;
    max_scroll_pct: number;
    click_count: number;
    utm_source: string | null;
    referrer: string | null;
    created_at: string;
  }[];
};

export type TokenStatsResponse = {
  summary: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    kie_credits: string;
    provider_cost_usd: string;
    provider_cost_rub: string;
    charged_rub: string;
    margin_rub: string;
    requests: number;
    pricing_note?: string;
  };
  daily: {
    date: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    provider_cost_usd: string;
    charged_rub: string;
    requests: number;
  }[];
};

export type LogRow = {
  kind: string;
  event_name: string;
  user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type RequestLogRow = {
  id: string;
  user_id: string;
  feature: string;
  model: string | null;
  input_units: number;
  output_units: number;
  provider_cost_usd: string;
  kie_credits?: string | null;
  charged_rub: string;
  created_at: string;
};

export type PaymentRow = {
  id: string;
  user_id: string;
  user_name: string | null;
  telegram_id: number;
  provider: string;
  provider_payment_id: string | null;
  purpose: string;
  purpose_label: string;
  status: string;
  status_label: string;
  amount_rub: string;
  admin_comment: string | null;
  created_at: string;
};

export type WithdrawalRow = {
  id: string;
  user_name: string | null;
  telegram_id: number;
  amount_rub: string;
  status: string;
  payout_details: Record<string, unknown>;
  admin_comment: string | null;
  created_at: string;
};

export type ReferralRow = {
  id: string;
  referrer_user_id: string;
  referrer_name: string | null;
  referrer_telegram_id: number;
  partner_reward_percent: number;
  referred_user_id: string;
  accrued_rub: string;
  reward_percent: number;
};

export type TarotCardRow = {
  id: string;
  slug: string;
  name: string;
  number: number;
  image_path: string;
};
