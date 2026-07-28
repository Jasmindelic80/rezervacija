from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import BlogCategory, BlogPost

POSTS = [
    {
        'category': 'Vodiči',
        'title': 'Kako online rezervacija termina štedi vrijeme klijentima i biznisima',
        'excerpt': 'Zašto sve više salona, klinika i servisa u BiH prelazi sa telefonskog zakazivanja na online rezervacije — i šta to znači za vas.',
        'content': '''
<p>Zakazivanje termina putem telefona zvuči jednostavno, ali u praksi klijent često mora zvati više puta dok ne dobije slobodan termin, a osoblje gubi dragocjeno vrijeme odgovarajući na pozive umjesto da radi svoj posao.</p>
<h2>Manje propuštenih poziva, manje čekanja</h2>
<p>Online rezervacija omogućava klijentu da u par klikova vidi slobodne termine i odmah zakaže uslugu, 0-24, bez čekanja da neko podigne telefon. Za biznis to znači manje prekinutog rada i manje izgubljenih klijenata koji odustanu jer nisu mogli dobiti vezu.</p>
<h2>Automatski podsjetnici smanjuju broj no-showova</h2>
<p>Sistem automatski šalje podsjetnik prije termina, što značajno smanjuje broj klijenata koji zaborave doći. To direktno utiče na prihod, jer prazan termin je izgubljen prihod koji se ne može nadoknaditi.</p>
<h2>Uvid u sve termine na jednom mjestu</h2>
<p>Umjesto papirnog kalendara ili nekoliko različitih grupa na Viberu, cijeli raspored je vidljiv na jednom mjestu — dostupan sa telefona ili računara, u svakom trenutku.</p>
''',
    },
    {
        'category': 'Za biznise',
        'title': '5 razloga zašto frizerski i kozmetički saloni trebaju online zakazivanje',
        'excerpt': 'Frizerski i kozmetički saloni imaju specifičan ritam rada — evo kako digitalno zakazivanje rješava njihove najveće svakodnevne probleme.',
        'content': '''
<p>Frizerski i kozmetički saloni rade sa velikim brojem kratkih termina dnevno, što telefonsko zakazivanje čini posebno zahtjevnim. Evo zašto je online sistem prirodno rješenje za ovu industriju.</p>
<h2>1. Klijent bira frizera i uslugu koju želi</h2>
<p>Umjesto generičkog termina, klijent unaprijed odabere konkretnu uslugu (šišanje, farbanje, manikir) i, ako želi, konkretnog izvođača — što skraćuje razgovor na minimum.</p>
<h2>2. Manje "praznog hoda" između klijenata</h2>
<p>Kada su termini jasno raspoređeni po trajanju usluge, salon lakše popuni cijeli radni dan bez rupa u rasporedu.</p>
<h2>3. Podsjetnici smanjuju otkazivanja u zadnji čas</h2>
<p>Automatski podsjetnik dan prije termina daje klijentu priliku da na vrijeme otkaže ili pomjeri termin, umjesto da se jednostavno ne pojavi.</p>
<h2>4. Nova klijentela putem pretrage</h2>
<p>Klijenti koji traže salon u svom gradu mogu pronaći biznis direktno kroz platformu, bez da su ranije čuli za njega.</p>
<h2>5. Manje administracije za vlasnika</h2>
<p>Umjesto ručnog vođenja evidencije, vlasnik salona u svakom trenutku vidi ko dolazi, kada i za šta — spremno za štampanje ili izvoz.</p>
''',
    },
    {
        'category': 'Za biznise',
        'title': 'Digitalizacija auto-servisa: kako online termini smanjuju gužve i čekanja',
        'excerpt': 'Auto-servisi se često suočavaju sa nagomilanim terminima i nejasnim procjenama trajanja popravke. Evo kako online zakazivanje to rješava.',
        'content': '''
<p>Za razliku od frizerskih salona, auto-servisi rade sa uslugama različitog trajanja — od brze zamjene ulja do dužih popravki. Bez jasnog sistema zakazivanja, to lako dovede do gužvi i nezadovoljnih klijenata.</p>
<h2>Jasno definisane usluge i trajanje</h2>
<p>Kada su usluge unaprijed definisane sa procijenjenim trajanjem, sistem automatski raspoređuje termine tako da se ne preklapaju, a mehaničari znaju tačno šta ih očekuje tokom dana.</p>
<h2>Klijent zna kada da dođe — bez čekanja u redu</h2>
<p>Umjesto da klijent dovede auto i čeka da dođe na red, on unaprijed zna tačno vrijeme termina, što oslobađa i njegovo vrijeme i prostor ispred servisa.</p>
<h2>Historija usluga na jednom mjestu</h2>
<p>Servis lako prati koji su klijenti već bili, koje usluge su ranije rađene i kada je vozilo za sljedeći pregled — što gradi povjerenje i olakšava ponovne posjete.</p>
''',
    },
    {
        'category': 'Za biznise',
        'title': 'Kako smanjiti broj otkazanih termina (no-show) u svom biznisu',
        'excerpt': 'Prazan termin je izgubljen prihod. Evo provjerenih načina da smanjite broj klijenata koji ne dođu na zakazani termin.',
        'content': '''
<p>Otkazani ili propušteni termini (tzv. no-show) jedan su od najvećih izvora izgubljenog prihoda za uslužne biznise. Srećom, postoji nekoliko jednostavnih mjera koje značajno smanjuju taj problem.</p>
<h2>Automatski podsjetnici</h2>
<p>Podsjetnik poslat dan ili nekoliko sati prije termina podsjeća klijenta da je zakazao i daje mu priliku da na vrijeme otkaže ako ne može doći, umjesto da se jednostavno ne pojavi.</p>
<h2>Jasna politika otkazivanja</h2>
<p>Kada klijent unaprijed zna do kada može besplatno otkazati termin, manja je vjerovatnoća posljednjeg trenutka iznenađenja za biznis.</p>
<h2>Jednostavno pomjeranje termina</h2>
<p>Ako je klijentu lako sam promijeniti termin na drugi datum, veća je šansa da će to i uraditi umjesto da termin jednostavno propusti.</p>
<h2>Praćenje redovnih klijenata</h2>
<p>Evidencija ranijih dolazaka pomaže da se prepozna ko redovno otkazuje u zadnji čas, pa se prema tim klijentima može postupati drugačije (npr. potvrda termina dan ranije).</p>
''',
    },
    {
        'category': 'Vodiči',
        'title': 'Kako izabrati pravu uslugu i termin kada rezervišete online',
        'excerpt': 'Kratak vodič za klijente — kako pretraživati biznise, čitati recenzije i odabrati termin koji najviše odgovara.',
        'content': '''
<p>Online rezervacija je jednostavna, ali nekoliko malih koraka može učiniti da odaberete baš onu uslugu i termin koji vam najviše odgovara.</p>
<h2>Pretraga po kategoriji i lokaciji</h2>
<p>Prvi korak je pronaći biznise u svom gradu koji nude uslugu koja vam treba — od frizerskih salona do automehaničara.</p>
<h2>Provjerite recenzije drugih korisnika</h2>
<p>Ocjene i komentari prethodnih klijenata daju realnu sliku o kvalitetu usluge i preciznosti održavanja termina.</p>
<h2>Odaberite uslugu, a ne samo "termin"</h2>
<p>Odabir konkretne usluge (a ne generičkog termina) osigurava da je rezervisano dovoljno vremena i da osoblje zna šta da pripremi.</p>
<h2>Sačuvajte potvrdu i podsjetnik</h2>
<p>Nakon rezervacije stiže potvrda, a kasnije i podsjetnik prije termina — tako da ne morate ništa pamtiti napamet.</p>
''',
    },
    {
        'category': 'Novosti',
        'title': 'Zašto smo napravili BookBiH: rezervacije termina prilagođene tržištu BiH',
        'excerpt': 'Priča o tome zašto smo pokrenuli platformu za online zakazivanje termina namijenjenu domaćim biznisima i klijentima u Bosni i Hercegovini.',
        'content': '''
<p>Većina alata za zakazivanje termina napravljena je za tržišta van Balkana i često ne uzima u obzir lokalne navike, jezik i način plaćanja. BookBiH je nastao kao odgovor na tu prazninu.</p>
<h2>Platforma na domaćem jeziku</h2>
<p>Cijela platforma je dostupna na bosanskom jeziku (uz mogućnost engleskog i njemačkog), što je posebno bitno za starije i manje "digitalne" korisnike, kao i biznise koji rade sa strankim tržištem.</p>
<h2>Podrška za lokalne biznise svih veličina</h2>
<p>Od jednog frizera u malom gradu do servisa sa više zaposlenih — sistem je napravljen da se prilagodi različitim veličinama i vrstama biznisa u FBiH, RS-u i Brčko Distriktu.</p>
<h2>Šta dalje</h2>
<p>Nastavljamo raditi na novim funkcijama na osnovu povratnih informacija biznisa i klijenata koji svakodnevno koriste platformu.</p>
''',
    },
    {
        'category': 'Vodiči',
        'title': 'Prednosti online plaćanja i pretplate za vlasnike biznisa',
        'excerpt': 'Kako pretplatnički model i online plaćanje pojednostavljuju upravljanje biznisom i smanjuju administrativni posao.',
        'content': '''
<p>Pored zakazivanja termina, mnogi biznisi traže i jednostavan način za praćenje troškova korištenja same platforme. Pretplatnički model rješava taj problem na predvidiv način.</p>
<h2>Predvidivi mjesečni trošak</h2>
<p>Umjesto skrivenih naknada po rezervaciji, pretplata daje jasnu i fiksnu mjesečnu cijenu, što olakšava planiranje budžeta biznisa.</p>
<h2>Online plaćanje bez odlaska na šalter</h2>
<p>Plaćanje putem kartice ili PayPal-a omogućava da se pretplata obnovi u nekoliko klikova, bez potrebe za fizičkom uplatnicom.</p>
<h2>Period probe prije obaveze plaćanja</h2>
<p>Prije nego što se biznis odluči na pretplatu, ima priliku isprobati sve funkcije platforme i vidjeti stvarnu korist za svoje poslovanje.</p>
''',
    },
    {
        'category': 'Za biznise',
        'title': 'Kako izgraditi povjerenje kroz recenzije i ocjene klijenata',
        'excerpt': 'Recenzije su danas jedan od najvažnijih faktora pri odabiru biznisa. Evo kako da ih iskoristite sebi u korist.',
        'content': '''
<p>Novi klijenti često prvo pogledaju ocjene i komentare prije nego što zakažu termin kod nepoznatog biznisa. Zato je upravljanje recenzijama važan dio svakodnevnog poslovanja.</p>
<h2>Zamolite zadovoljne klijente za recenziju</h2>
<p>Najbolji trenutak da zatražite recenziju je odmah nakon uspješno završene usluge, dok je iskustvo još svježe.</p>
<h2>Odgovorite i na pozitivne i na negativne komentare</h2>
<p>Profesionalan odgovor na negativnu recenziju pokazuje potencijalnim klijentima da vam je stalo do kvaliteta usluge, čak i kada nešto pođe po zlu.</p>
<h2>Konzistentnost gradi reputaciju</h2>
<p>Redovno visoke ocjene tokom vremena imaju mnogo veći efekat na povjerenje nego pojedinačna odlična recenzija.</p>
''',
    },
]


class Command(BaseCommand):
    help = 'Puni blog sa početnim setom kategorija i objavljenih članaka'

    def handle(self, *args, **kwargs):
        created_posts = 0
        for entry in POSTS:
            category, _ = BlogCategory.objects.get_or_create(name=entry['category'])

            post, created = BlogPost.objects.get_or_create(
                title=entry['title'],
                defaults={
                    'slug': slugify(entry['title'])[:50].rstrip('-'),
                    'category': category,
                    'excerpt': entry['excerpt'],
                    'content': entry['content'].strip(),
                    'is_published': True,
                    'published_at': timezone.now(),
                },
            )
            if created:
                created_posts += 1

        if created_posts:
            self.stdout.write(self.style.SUCCESS(f'Kreirano {created_posts} novih blog članaka.'))
        else:
            self.stdout.write('Svi blog članci već postoje.')
