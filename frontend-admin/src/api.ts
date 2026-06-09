const BASE = "/admin-api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function patch(path: string, params: Record<string, string>) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE}${path}?${qs}`, { method: "PATCH" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function del(path: string) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  dashboard: () => get<Record<string, number | string>>("/dashboard"),
  signups: (days = 30) => get<{ date: string; count: number }[]>(`/stats/signups?days=${days}`),
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
    const res = await fetch(`${BASE}/tarot-cards/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
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
  created_at: string;
};

export type BillingData = {
  payments: { id: string; purpose: string; status: string; amount_rub: string; created_at: string }[];
  usage: BillingUsageRow[];
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
  referrer_name: string | null;
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
