FROM python:3.12-slim

# Postavi working directory
WORKDIR /app

# Sistemske dependencije
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instaliraj Python pakete
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiraj kod
COPY . .

# Kreiraj potrebne foldere
RUN mkdir -p logs media staticfiles static

# Postavi environment varijable
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

# Sakupi static fajlove
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Pokretanje
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
