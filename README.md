# AutoParts CRM

**Профессиональная система учета и продажи автозапчастей с CRM**

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Запуск сервера

```bash
python manage.py runserver
```

Или через лаунчер (автооткрытие браузера):

```bash
python run_server.py
```

### 4. Регистрация

Откройте http://127.0.0.1:8000/ в браузере и зарегистрируйте первый аккаунт (он будет администратором).

---

## 📦 Сборка в .exe

### Шаг 1: Установите PyInstaller

```bash
pip install pyinstaller
```

### Шаг 2: Соберите проект

```bash
pyinstaller build.spec
```

### Шаг 3: Запуск

Готовый файл `AutoPartsCRM.exe` будет в папке `dist/`.

При запуске:
- Автоматически создается/обновляется база данных
- Запускается Django-сервер
- Открывается браузер на http://127.0.0.1:8000/
- Работает полностью офлайн

---

## 🧩 Структура проекта

```
program/
├── manage.py                  # Django management
├── run_server.py              # Standalone launcher
├── build.spec                 # PyInstaller config
├── requirements.txt           # Dependencies
├── db.sqlite3                 # SQLite database
│
├── autoparts/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── users/                     # Auth & user management
│   ├── models.py              # Custom User (email + roles)
│   ├── views.py               # Login, Register, Dashboard
│   ├── forms.py               # LoginForm, RegisterForm
│   ├── urls.py
│   └── admin.py
│
├── catalog/                   # Product catalog
│   ├── models.py              # Product, Category
│   ├── views.py               # CRUD, Search, Import
│   ├── forms.py               # ProductForm, ImportForm
│   ├── urls.py
│   └── admin.py
│
├── warehouse/                 # Stock management
│   ├── models.py              # StockMovement
│   ├── views.py               # Stock list, adjustments
│   ├── urls.py
│   └── admin.py
│
├── orders/                    # Sales / orders
│   ├── models.py              # Order, OrderItem
│   ├── views.py               # Create, list, status
│   ├── forms.py               # OrderForm
│   ├── urls.py
│   └── admin.py
│
├── crm/                       # Client management
│   ├── models.py              # Client
│   ├── views.py               # CRUD, history
│   ├── forms.py               # ClientForm
│   ├── urls.py
│   └── admin.py
│
├── reports/                   # Analytics
│   ├── views.py               # Sales, products, stock reports
│   └── urls.py
│
├── static/
│   ├── css/style.css          # Dark glassmorphism theme
│   └── js/main.js             # UI interactions
│
└── templates/
    ├── base.html              # Main layout (sidebar + navbar)
    ├── dashboard.html         # Dashboard with stats
    ├── users/
    │   ├── login.html
    │   └── register.html
    ├── catalog/
    │   ├── list.html
    │   ├── detail.html
    │   ├── form.html
    │   ├── import.html
    │   ├── categories.html
    │   └── confirm_delete.html
    ├── warehouse/
    │   ├── list.html
    │   └── movements.html
    ├── orders/
    │   ├── list.html
    │   ├── detail.html
    │   └── create.html
    ├── crm/
    │   ├── list.html
    │   ├── detail.html
    │   ├── form.html
    │   └── confirm_delete.html
    └── reports/
        └── index.html
```

---

## ⚙️ Переключение на PostgreSQL

В `autoparts/settings.py` замените блок `DATABASES`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'autoparts_db',
        'USER': 'postgres',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Установите драйвер: `pip install psycopg2-binary`

---

## 📥 Импорт прайс-листа

Поддерживаемые форматы: `.xlsx`, `.xls`, `.csv`

Автоматическое определение столбцов:
| Поле | Варианты названий столбцов |
|------|--------------------------|
| OEM номер | oem, oem_number, оем |
| Артикул | артикул, part_number, арт |
| Название | название, name, наименование |
| Цена | цена, price, розничная цена |
| Остаток | остаток, stock, количество, кол-во |
| Бренд | бренд, brand, производитель |
| Категория | категория, category, группа |
