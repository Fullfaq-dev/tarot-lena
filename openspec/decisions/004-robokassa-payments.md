# ADR-004: Robokassa как платёжный провайдер

**Статус:** Принято  
**Дата:** 2026-07-26

## Контекст

Platega не используется в проде. Нужна приёмка оплаты через Robokassa с ResultURL на наш API.

## Решение

1. **Провайдер:** `RobokassaProvider` + `POST/GET /callbacks/robokassa`.
2. **Подпись:** MD5. Оплата — `MerchantLogin:OutSum:InvId:Password1[:Shp_*]`. Result — `OutSum:InvId:Password2[:Shp_*]`. Ответ ResultURL — `OK{InvId}`.
3. **InvId:** целое из Redis `INCR robokassa:inv_id`; UUID платежа в `Shp_payment_id`.
4. **Success/Fail:** существующие `/payment/success` и `/payment/failed` (не fulfillment).
5. **Демо:** `PAYMENTS_DEMO_MODE=1` или отсутствие ключей Robokassa → мгновенный `complete_payment` без редиректа.
6. Platega-код оставляем в репозитории, но create-path идёт через Robokassa.

## Кабинет Robokassa (прод, IP)

- Result URL: `http://85.234.106.108/callbacks/robokassa` (POST)
- Success URL: `http://85.234.106.108/payment/success` (GET)
- Fail URL: `http://85.234.106.108/payment/failed` (GET)

Нельзя ставить `https://t.me/...` в ResultURL — сервер не получит уведомление.

## Последствия

- Нужны `ROBOKASSA_MERCHANT_LOGIN`, `PASSWORD1`, `PASSWORD2` в `.env`.
- При firewall — whitelist IP Robokassa.
- Фискальный `Receipt` пока не передаём.
