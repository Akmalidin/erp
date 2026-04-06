# AutoParts CRM — Project Guide

## Stack
- Django 4.2, SQLite, Python 3.x
- Gunicorn + Nginx on VPS (46.149.68.65)
- Live: https://1.erp.tw1.su

## Apps
- `users/` — кастомный User (email-логин, валюта, роль)
- `catalog/` — товары, категории, наценки, матрица авто, импорт
- `orders/` — заказы, POS касса, скидки
- `crm/` — клиенты, долги, смены, платежи
- `warehouse/` — склады, остатки, перемещения, инвентаризация
- `purchases/` — закупки, поставщики
- `reports/` — отчёты, ABC-анализ

## Deploy
```bash
cd C:/Users/VERTEX/Desktop
python update.py
```
Скрипт: SFTP-загрузка файлов → migrate → restart gunicorn.

## Superadmin
- Email: `akmalmadakimov6@gmail.com`
- Панель: https://1.erp.tw1.su/superadmin/
- Блокировка/разблокировка пользователей, смена паролей, просмотр данных

## Key Models
- `Order`: discount_type (none/percent/fixed), discount_value
- `OrderItem`: discount_percent (per-item скидка)
- `PriceLevel`: markup_percent, is_default
- `CarMake` → `CarModel` → `Product.compatible_models` (M2M)

## Conventions
- Валюта: всегда `{{ user.currency_symbol }}` / `{{ request.user.currency_symbol }}`, не хардкодить ₸
- Тема: по умолчанию светлая (light), переключатель в navbar
- Сайдбар: toggle через .app-layout.sidebar-collapsed, состояние в localStorage ('sidebar_collapsed')
- Колонки каталога: localStorage key 'catalog_col_prefs_v2'

## Migrations
После изменения models.py создавать файл в `<app>/migrations/` вручную (сервер без makemigrations).
Текущая последняя миграция orders: `0006_order_discount_orderitem_discount_percent`

## Server paths
- Project: `/var/www/erp/`
- Venv: `/var/www/erp/venv/`
- Service: `erp_gunicorn`
- Nginx config: `/etc/nginx/sites-available/1.erp.tw1.su`
