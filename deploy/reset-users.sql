-- Сброс всех пользователей бота (админ-панель и колода таро сохраняются).
-- Запуск: docker compose -f docker-compose.prod.yml exec -T postgres \
--   psql -U tarot -d tarot -f - < deploy/reset-users.sql

BEGIN;

TRUNCATE TABLE
  analytics_events,
  landing_events,
  landing_sessions,
  notification_logs,
  notifications,
  generated_reports,
  referral_withdrawal_requests,
  referrals,
  usage_records,
  balance_transactions,
  payments,
  product_entitlements,
  product_usages,
  voice_messages,
  media_jobs,
  daily_predictions,
  tarot_readings,
  relationship_mentions,
  relationship_events,
  relationship_people,
  memories,
  messages,
  onboarding_sessions,
  soul_profiles,
  subscriptions,
  user_settings,
  users
RESTART IDENTITY CASCADE;

COMMIT;
