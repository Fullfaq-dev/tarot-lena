-- One-time fix when alembic was stamped to head without running 202607130001.
ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS morning_digest_enabled BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS weekly_horoscope_enabled BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS free_morning_week_ends_at DATE;

ALTER TABLE user_settings
  ADD COLUMN IF NOT EXISTS mini_portrait_sent_at TIMESTAMPTZ;

UPDATE user_settings
SET morning_digest_enabled = daily_card_enabled,
    weekly_horoscope_enabled = true
WHERE morning_digest_enabled IS DISTINCT FROM daily_card_enabled
   OR weekly_horoscope_enabled IS DISTINCT FROM true;
