# RezervišiBiH — Django Aplikacija za Rezervacije Termina

Platforma slična Doctorlibу ali za uslužne djelatnosti u BiH
(frizeri, kozmetičari, automehaničari, stomatolozi, itd.)

---

## 📁 Struktura Projekta

```
rezervisi_bih/
├── manage.py
├── requirements.txt
├── .env.example
├── config/                  # Django settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/            # Korisnici (klijenti + pružatelji usluga)
│   ├── businesses/          # Saloni, frizerski saloni, itd.
│   ├── services/            # Usluge koje nudi svaki biznis
│   ├── appointments/        # Rezervacije termina
│   ├── availability/        # Radno vrijeme i slobodni termini
│   └── notifications/       # Email/SMS notifikacije
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── search/
│   ├── businesses/
│   └── appointments/
└── static/
    ├── css/
    ├── js/
    └── img/
```

---

## ⚙️ Instalacija

```bash
# 1. Kloniraj / napravi projekt
django-admin startproject config .
mkdir -p apps/accounts apps/businesses apps/services apps/appointments apps/availability

# 2. Instaliraj dependencije
pip install -r requirements.txt

# 3. Postavi .env fajl
cp .env.example .env
# Uredi .env sa svojim podacima

# 4. Migracije
python manage.py makemigrations
python manage.py migrate

# 5. Superuser
python manage.py createsuperuser

# 6. Pokrni server
python manage.py runserver
```

---

## 📦 requirements.txt

```
Django>=4.2
djangorestframework>=3.15
django-allauth>=0.61          # Auth (Google, Facebook login)
django-crispy-forms>=2.1
crispy-bootstrap5>=0.7
Pillow>=10.0                  # Slike profila
django-environ>=0.11          # .env fajlovi
psycopg2-binary>=2.9          # PostgreSQL
celery>=5.3                   # Async zadaci
redis>=5.0                    # Celery broker
django-celery-beat>=2.5       # Periodični taskovi
whitenoise>=6.6               # Static fajlovi
gunicorn>=21.0                # Production server
django-filter>=23.5           # Filtriranje rezultata
geopy>=2.4                    # Geolokacija
django-leaflet>=0.29          # Mapa
```

---

## 🗄️ Modeli (Ključni)

### accounts/models.py
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CLIENT = 'client'
    ROLE_PROVIDER = 'provider'
    ROLES = [(ROLE_CLIENT, 'Klijent'), (ROLE_PROVIDER, 'Pružatelj usluge')]
    
    role = models.CharField(max_length=20, choices=ROLES, default=ROLE_CLIENT)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    
    def is_provider(self):
        return self.role == self.ROLE_PROVIDER
```

### businesses/models.py
```python
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)          # "Frizer", "Kozmetika"
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50)            # emoji ili icon klasa
    
    def __str__(self):
        return self.name

class Business(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='businesses')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)           # Sarajevo, Banja Luka...
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='business_logos/', blank=True)
    cover_image = models.ImageField(upload_to='business_covers/', blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # Verificiran od admina
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Businesses'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(r.rating for r in reviews) / len(reviews)
        return 0

class Staff(models.Model):
    """Radnici u biznisu (npr. frizerski majstori)"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='staff_photos/', blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} @ {self.business.name}"

class Review(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='reviews')
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('business', 'client')
```

### services/models.py
```python
from django.db import models

class Service(models.Model):
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)         # "Šišanje", "Bojanje kose"
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField() # Trajanje u minutama
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min) - {self.price} KM"
```

### availability/models.py
```python
from django.db import models

DAYS = [
    (0, 'Ponedjeljak'), (1, 'Utorak'), (2, 'Srijeda'),
    (3, 'Četvrtak'), (4, 'Petak'), (5, 'Subota'), (6, 'Nedjelja')
]

class WorkingHours(models.Model):
    """Radno vrijeme biznisa po danima"""
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='working_hours')
    staff = models.ForeignKey('businesses.Staff', on_delete=models.CASCADE, null=True, blank=True)
    day_of_week = models.IntegerField(choices=DAYS)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('business', 'staff', 'day_of_week')

class BlockedSlot(models.Model):
    """Blokiran termin (pauza, odmor, godišnji)"""
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE)
    staff = models.ForeignKey('businesses.Staff', on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
```

### appointments/models.py
```python
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Appointment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_NO_SHOW = 'no_show'
    
    STATUSES = [
        (STATUS_PENDING, 'Na čekanju'),
        (STATUS_CONFIRMED, 'Potvrđen'),
        (STATUS_CANCELLED, 'Otkazan'),
        (STATUS_COMPLETED, 'Završen'),
        (STATUS_NO_SHOW, 'Nije se pojavio'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE)
    service = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True)
    staff = models.ForeignKey('businesses.Staff', on_delete=models.SET_NULL, null=True, blank=True)
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)             # Napomene klijenta
    cancellation_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_datetime']
    
    def __str__(self):
        return f"{self.client} → {self.business} | {self.start_datetime:%d.%m.%Y %H:%M}"
```

---

## 🔍 Ključna Logika — Slobodni Termini

### availability/utils.py
```python
from datetime import datetime, timedelta, date
from appointments.models import Appointment
from .models import WorkingHours, BlockedSlot

def get_available_slots(business, service, staff=None, target_date=None):
    """
    Vraća listu slobodnih termina za dati dan.
    """
    if target_date is None:
        target_date = date.today()
    
    duration = timedelta(minutes=service.duration_minutes)
    day_of_week = target_date.weekday()
    
    # 1. Provjeri radno vrijeme
    wh_query = WorkingHours.objects.filter(
        business=business, day_of_week=day_of_week, is_closed=False
    )
    if staff:
        wh_query = wh_query.filter(staff=staff)
    
    working_hours = wh_query.first()
    if not working_hours:
        return []
    
    # 2. Generiši sve potencijalne termine (svakih 15/30 min)
    slot_interval = timedelta(minutes=15)
    slots = []
    current = datetime.combine(target_date, working_hours.open_time)
    end_of_day = datetime.combine(target_date, working_hours.close_time)
    
    while current + duration <= end_of_day:
        slots.append(current)
        current += slot_interval
    
    # 3. Ukloni zauzete termine
    existing_appointments = Appointment.objects.filter(
        business=business,
        start_datetime__date=target_date,
        status__in=['pending', 'confirmed']
    )
    if staff:
        existing_appointments = existing_appointments.filter(staff=staff)
    
    def is_slot_free(slot_start):
        slot_end = slot_start + duration
        for appt in existing_appointments:
            # Provjeri overlap
            if not (slot_end <= appt.start_datetime or slot_start >= appt.end_datetime):
                return False
        return True
    
    # 4. Ukloni blokirane termine
    blocked = BlockedSlot.objects.filter(
        business=business,
        start_datetime__date=target_date
    )
    if staff:
        blocked = blocked.filter(staff=staff)
    
    available = []
    for slot in slots:
        slot_end = slot + duration
        is_blocked = any(
            not (slot_end <= b.start_datetime or slot >= b.end_datetime)
            for b in blocked
        )
        if is_slot_free(slot) and not is_blocked:
            available.append(slot)
    
    return available
```

---

## 🌐 URL Struktura

```python
# config/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.businesses.urls')),       # Početna, pretraga
    path('termin/', include('apps.appointments.urls')),
    path('profil/', include('apps.accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('api/', include('apps.appointments.api_urls')),  # DRF za AJAX
]

# businesses/urls.py
urlpatterns = [
    path('', views.home, name='home'),
    path('pretraga/', views.search, name='search'),
    path('kategorija/<slug:slug>/', views.category, name='category'),
    path('biznis/<slug:slug>/', views.business_detail, name='business_detail'),
    path('biznis/registracija/', views.register_business, name='register_business'),
]

# appointments/urls.py
urlpatterns = [
    path('novi/<slug:business_slug>/', views.book_appointment, name='book'),
    path('potvrda/<uuid:pk>/', views.appointment_confirm, name='confirm'),
    path('otkazi/<uuid:pk>/', views.cancel_appointment, name='cancel'),
    path('moji-termini/', views.my_appointments, name='my_appointments'),
    # API za slobodne termine (AJAX)
    path('api/slobodni-termini/', views.available_slots_api, name='slots_api'),
]
```

---

## 🗺️ Ključne Stranice

| Stranica | Opis |
|----------|------|
| `/` | Početna — pretraga po kategoriji i gradu |
| `/pretraga/?kategorija=frizer&grad=Sarajevo` | Lista biznisa s filterima |
| `/biznis/salon-ana/` | Profil biznisa + kalendar termina |
| `/termin/novi/salon-ana/` | Wizard za rezervaciju (korak po korak) |
| `/moji-termini/` | Klijentova dashboard |
| `/dashboard/` | Provider dashboard (statistike, upravljanje) |

---

## 🛠️ Sljedeći Koraci

1. **Faza 1 – MVP**
   - [ ] Postavi Django projekt i modele
   - [ ] Admin panel za upravljanje
   - [ ] Registracija/login (allauth)
   - [ ] Pretraga biznisa
   - [ ] Rezervacija termina (basic)

2. **Faza 2 – Notifikacije**
   - [ ] Email potvrda rezervacije (Celery)
   - [ ] SMS podsjetnik (Twilio ili lokal. provider)
   - [ ] Podsjetnik 24h unaprijed

3. **Faza 3 – Napredne funkcije**
   - [ ] Mapa (Leaflet.js + OpenStreetMap)
   - [ ] Ocjene i recenzije
   - [ ] Provider statistike
   - [ ] Online plaćanje (integrisati lokalni gateway)

4. **Faza 4 – Mobile**
   - [ ] REST API (DRF) za mobilnu aplikaciju
   - [ ] PWA podrška

---

## 💡 Kategorije za BiH Tržište

- ✂️ Frizeri i barberi
- 💅 Kozmetički saloni
- 💆 Masaže i wellness
- 🦷 Stomatološke ordinacije
- 👨‍⚕️ Privatne ordinacije
- 🚗 Automehaničari i serviseri
- 🐾 Veterinari
- 📚 Privatni instruktori
- 🏋️ Personal traineri
- 🔧 Majstori i servisi
