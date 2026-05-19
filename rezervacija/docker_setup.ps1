# ============================================================
# docker_setup.ps1 — Automatski setup za Windows PowerShell
# Pokreni: .\docker_setup.ps1
# ============================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     RezervišiBiH — Docker Setup          ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# 1. Provjeri Docker
Write-Host "🐳 Provjera Docker instalacije..." -ForegroundColor Cyan
try {
    docker --version | Out-Null
    Write-Host "   ✓ Docker je instaliran" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Docker nije instaliran!" -ForegroundColor Red
    Write-Host "   Preuzmi sa: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# 2. Provjeri docker-compose
try {
    docker compose version | Out-Null
    Write-Host "   ✓ Docker Compose je dostupan" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Docker Compose nije dostupan!" -ForegroundColor Red
    exit 1
}

# 3. Kreiraj .env.docker ako ne postoji
if (-not (Test-Path ".env.docker")) {
    Write-Host "⚙️  Kreiram .env.docker fajl..." -ForegroundColor Cyan
    Copy-Item ".env.docker.example" ".env.docker" -ErrorAction SilentlyContinue
    Write-Host "   ✓ .env.docker kreiran" -ForegroundColor Green
} else {
    Write-Host "   ✓ .env.docker već postoji" -ForegroundColor Green
}

# 4. Build Docker image
Write-Host ""
Write-Host "🔨 Buildanje Docker imagea (može trajati 2-3 minute)..." -ForegroundColor Cyan
docker compose build

# 5. Pokretanje kontejnera
Write-Host ""
Write-Host "🚀 Pokretanje svih servisa..." -ForegroundColor Cyan
docker compose up -d

# 6. Čekaj da se baza inicijalizuje
Write-Host "⏳ Čekam inicijalizaciju baze (15 sekundi)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# 7. Kreiraj superusera
Write-Host ""
Write-Host "👤 Kreiranje admin korisnika..." -ForegroundColor Cyan
Write-Host "   (Unesi username, email i lozinku)" -ForegroundColor Yellow
docker compose exec web python manage.py createsuperuser

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✅ Setup završen!                       ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║                                          ║" -ForegroundColor Green
Write-Host "║  🌐 App:   http://localhost:8000         ║" -ForegroundColor Green
Write-Host "║  ⚙️  Admin: http://localhost:8000/admin   ║" -ForegroundColor Green
Write-Host "║                                          ║" -ForegroundColor Green
Write-Host "║  Zaustavi: docker compose down           ║" -ForegroundColor Green
Write-Host "║  Pokreni:  docker compose up -d          ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
