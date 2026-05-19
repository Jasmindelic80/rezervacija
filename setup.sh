#!/bin/bash
# ============================================================
# setup.sh — Automatska instalacija i postavljanje projekta
# Pokreni: chmod +x setup.sh && ./setup.sh
# ============================================================

set -e  # Zaustavi se pri grešci

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     RezervišiBiH — Setup Skript          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 1. Kreiranje virtualnog okruženja
echo "📦 Kreiranje virtualnog okruženja..."
python3 -m venv venv
source venv/bin/activate

# 2. Instalacija dependencija
echo "⬇️  Instalacija Python paketa..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. Kreiranje .env fajla
if [ ! -f .env ]; then
  echo "⚙️  Kreiranje .env fajla..."
  cp .env.example .env
  # Generiši random SECRET_KEY
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  sed -i "s/PROMIJENI-OVO-OBAVEZNO/$SECRET/" .env
  echo "   ✓ .env kreiran (popunite API ključeve u .env fajlu)"
else
  echo "   ✓ .env već postoji"
fi

# 4. Kreiranje foldera
echo "📁 Kreiranje potrebnih foldera..."
mkdir -p logs media static staticfiles

# 5. Migracije
echo "🗄️  Pokretanje migracija..."
python manage.py makemigrations accounts
python manage.py makemigrations businesses
python manage.py makemigrations services
python manage.py makemigrations availability
python manage.py makemigrations appointments
python manage.py makemigrations notifications
python manage.py migrate

# 6. Učitavanje kategorija
echo "🗂️  Učitavanje BiH kategorija..."
python manage.py loaddata fixtures/categories_bih.json

# 7. Static fajlovi
echo "🎨 Prikupljanje static fajlova..."
python manage.py collectstatic --noinput -v 0

# 8. Superuser (opciono)
echo ""
echo "👤 Kreirati admin superusera? (y/n)"
read -r CREATE_SU
if [ "$CREATE_SU" = "y" ]; then
  python manage.py createsuperuser
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✅ Setup završen!                       ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  Pokretanje:                             ║"
echo "║    source venv/bin/activate              ║"
echo "║    python manage.py runserver            ║"
echo "║                                          ║"
echo "║  Za notifikacije (novi terminali):        ║"
echo "║    celery -A config worker -l info       ║"
echo "║    celery -A config beat -l info         ║"
echo "║                                          ║"
echo "║  Admin panel: http://localhost:8000/admin ║"
echo "╚══════════════════════════════════════════╝"


# ============================================================
# KOMPLETNA STRUKTURA PROJEKTA
# ============================================================
: '
rezervisi_bih/
├── manage.py
├── setup.sh                   ← Ovaj fajl
├── requirements.txt
├── .env.example
├── .env                       ← Kreiran setupom (ne commitati!)
├── .gitignore
│
├── config/
│   ├── __init__.py            ← Importuje celery_app
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
│
├── apps/
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── models.py          ← User, PhoneOTP
│   │   ├── views.py           ← 3-koračna registracija
│   │   ├── login_views.py     ← Prijava brojem telefona
│   │   ├── forms.py           ← PhoneInputForm, OTPVerifyForm, itd.
│   │   ├── sms.py             ← SMS slanje
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── businesses/
│   │   ├── models.py          ← Business, Category, Staff, Review
│   │   ├── views.py           ← home, search, detail, slots_api
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── services/
│   │   ├── models.py          ← Service, ServiceCategory, StaffService
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── availability/
│   │   ├── models.py          ← WorkingHours, BlockedSlot
│   │   ├── utils.py           ← get_available_slots(), get_next_available_date()
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── appointments/
│   │   ├── models.py          ← Appointment (UUID PK)
│   │   ├── views.py           ← book, confirm, cancel, my_appointments
│   │   ├── provider_views.py  ← provider_dashboard
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   └── notifications/
│       ├── models.py          ← NotificationPreference, NotificationLog
│       ├── dispatcher.py      ← NotificationDispatcher (Viber→WA→SMS)
│       ├── tasks.py           ← Celery taskovi (potvrda, podsjetnici)
│       ├── views.py           ← notification_settings
│       ├── urls.py
│       ├── admin.py
│       ├── channels/
│       │   ├── viber.py       ← Infobip Viber API
│       │   ├── whatsapp.py    ← Meta WhatsApp Cloud API
│       │   └── sms.py         ← Twilio SMS fallback
│       └── migrations/
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── search/
│   │   └── results.html
│   ├── businesses/
│   │   └── detail.html
│   ├── appointments/
│   │   ├── book.html          ← 4-koračni wizard s kalendarom
│   │   ├── confirm.html
│   │   ├── cancel.html
│   │   └── my_appointments.html
│   ├── accounts/
│   │   ├── register_phone.html    ← Korak 1: Unos broja
│   │   ├── register_verify.html   ← Korak 2: OTP verifikacija
│   │   ├── register_complete.html ← Korak 3: Profil
│   │   ├── login.html
│   │   └── notification_settings.html
│   └── provider/
│       └── dashboard.html
│
├── static/
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   └── main.js
│   └── img/
│
├── fixtures/
│   └── categories_bih.json    ← 20 BiH kategorija
│
├── logs/
│   └── app.log
│
└── media/
    ├── avatars/
    ├── business_logos/
    ├── business_covers/
    ├── business_gallery/
    └── staff_photos/
'


# ============================================================
# .gitignore
# ============================================================
: '
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
venv/
env/
.env

# Django
*.log
db.sqlite3
media/
staticfiles/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
'
