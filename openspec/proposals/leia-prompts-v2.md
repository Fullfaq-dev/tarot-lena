# Промпты Леи по ТЗ заказчицы

## Summary

Адаптация промптов Telegram-бота «Лея» под документ заказчицы:
`system = ОСНОВНОЙ ПРОМТ + "\n\n" + БЛОК`, переменные считает бэкенд,
мини ≠ укороченная полная, ежедневная рассылка без «карты дня».

## Changes

- `prompts/system_ru.md` — часть 1 (голос, формула, запреты, границы).
- `prompts/leia/*.md` — полные/мини продукты + daily_sign/daily_personal/weekly.
- `backend/app/services/products/prompts.py` — сборщик `assemble_system` / `product_system`.
- `NumerologyService.prompt_vars` + `personal_day` / `personal_month` / `month_arcana`.
- Продуктовая генерация: system = main+block, user = короткий trigger.
- Утро: слой знака (кэш 12) + персональное уточнение + `{last_7}`.
- Неделя: AI по знаку + аркан недели; карта дня убрана из утра.

## Mapping продуктов

| product_id | Блок full | Блок mini |
|---|---|---|
| love | full_love | mini_love |
| question | full_question | mini_question |
| tarot_spread | full_tarot | mini_tarot |
| wealth | full_wealth | mini_wealth |
| forecast | full_matrix | mini_matrix |
| negative | full_negative | mini_negative |

`full_month` / `mini_month` — готовы к отдельному продукту «прогноз на месяц».
