import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.businesses.models import Business, Review

User = get_user_model()

DEMO_CLIENTS = [
    ('Amina', 'Hodžić', '+38760100001'),
    ('Damir', 'Kovačević', '+38760100002'),
    ('Selma', 'Begić', '+38760100003'),
    ('Emir', 'Halilović', '+38760100004'),
    ('Lejla', 'Softić', '+38760100005'),
    ('Haris', 'Mujić', '+38760100006'),
    ('Amela', 'Zukić', '+38760100007'),
    ('Tarik', 'Salihović', '+38760100008'),
    ('Mirela', 'Đulić', '+38760100009'),
    ('Adna', 'Karić', '+38760100010'),
]

REVIEWS_BY_CATEGORY = {
    'Frizeri i barberi': [
        (5, 'Odličan šišanje, tačno ono što sam tražila. Zakazivanje online je bilo brzo i jednostavno.'),
        (5, 'Profesionalno osoblje i ugodna atmosfera. Preporučujem svima u komšiluku.'),
        (4, 'Dobra usluga, malo sam čekao iako sam imao termin, ali rezultat je odličan.'),
        (5, 'Najbolji frizer kod kojeg sam bio, redovno se vraćam.'),
    ],
    'Automehaničari': [
        (5, 'Brzo i kvalitetno servisirali auto, cijena kako je i navedeno prilikom zakazivanja.'),
        (4, 'Sve je obavljeno u dogovorenom terminu, samo bi mogli malo bolje objasniti šta je urađeno.'),
        (5, 'Pošteni majstori, ne naplaćuju nepotrebne stvari. Zakazivanje termina uštedjelo mi puno vremena.'),
        (5, 'Odlična dijagnostika kvara, riješeno iz prve.'),
    ],
    'Kozmetički saloni': [
        (5, 'Prekrasan tretman lica, koža mi izgleda odlično. Sve pohvale za higijenu salona.'),
        (5, 'Ljubazno osoblje i vrhunska usluga, termin je počeo tačno na vrijeme.'),
        (4, 'Zadovoljna sam uslugom, samo bih voljela veći izbor termina popodne.'),
    ],
    'Veterinari': [
        (5, 'Veoma pažljivi prema mom psu, sve objašnjeno detaljno i strpljivo.'),
        (5, 'Brz termin za hitan slučaj, spasili su mi mačku. Neizmjerno zahvalna.'),
        (4, 'Kvalitetna usluga, cijene su fer u odnosu na ostale veterinarske stanice.'),
    ],
    'Masaže i wellness': [
        (5, 'Potpuno opuštanje, masaža je bila upravo ono što mi je trebalo poslije napornog radnog tjedna.'),
        (5, 'Ugodan ambijent i stručno osoblje. Online zakazivanje termina mi je olakšalo organizaciju.'),
        (4, 'Dobar tretman, samo je prostor malo bučniji nego što sam očekivala.'),
    ],
    'Personal treneri': [
        (5, 'Trener je napravio program treninga skroj po mjeri, vidim napredak već poslije par sedmica.'),
        (5, 'Motivišuć i strpljiv, preporučujem svima koji tek počinju sa treninzima.'),
        (4, 'Odličan trening, jedino bih volio da ima više slobodnih termina uveče.'),
    ],
    'Optičari': [
        (5, 'Precizan pregled vida i veliki izbor okvira. Naočale su gotove prije najavljenog roka.'),
        (4, 'Ljubazno osoblje, sve objašnjeno oko izbora stakala.'),
        (5, 'Brzo i profesionalno, cijena povoljnija nego kod konkurencije.'),
    ],
    'Privatni instruktori': [
        (5, 'Instruktor mi je pomogao da savladam gradivo koje mi je dugo pravilo problem, izuzetno strpljiv.'),
        (5, 'Časovi su organizovani i prilagođeni mom tempu, vidim veliki napredak.'),
        (4, 'Kvalitetne instrukcije, samo bi termin mogao trajati malo duže.'),
    ],
}

GENERIC_REVIEWS = [
    (5, 'Odlična usluga, sve preporuke. Zakazivanje termina online je bilo jednostavno i brzo.'),
    (4, 'Zadovoljan sam uslugom, termin je bio tačno kada je i zakazan.'),
    (5, 'Profesionalan pristup i ljubazno osoblje, definitivno se vraćam ponovo.'),
]


class Command(BaseCommand):
    help = 'Puni recenzije demo klijenata za postojeće biznise'

    def handle(self, *args, **kwargs):
        clients = []
        for first_name, last_name, phone in DEMO_CLIENTS:
            user, _ = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'username': phone,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': User.ROLE_CLIENT,
                    'phone_verified': True,
                },
            )
            clients.append(user)

        created_count = 0
        for business in Business.objects.all():
            category_name = business.category.name if business.category else None
            pool = REVIEWS_BY_CATEGORY.get(category_name, GENERIC_REVIEWS)

            reviewers = random.sample(clients, k=min(len(clients), random.randint(3, 5)))
            for i, client in enumerate(reviewers):
                rating, comment = random.choice(pool)
                review, created = Review.objects.get_or_create(
                    business=business,
                    client=client,
                    defaults={
                        'rating': rating,
                        'comment': comment,
                        'is_approved': True,
                    },
                )
                if created:
                    days_ago = random.randint(1, 90)
                    Review.objects.filter(pk=review.pk).update(
                        created_at=timezone.now() - timedelta(days=days_ago)
                    )
                    created_count += 1

        if created_count:
            self.stdout.write(self.style.SUCCESS(f'Kreirano {created_count} novih recenzija.'))
        else:
            self.stdout.write('Sve recenzije već postoje.')
