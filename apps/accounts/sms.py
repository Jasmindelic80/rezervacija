import environ
from django.conf import settings

env = environ.Env()


def send_otp_sms(phone: str, otp: str, purpose: str = 'register') -> bool:
    """
    Šalje OTP SMS putem Twilio ili Infobip.
    Vraća True ako je uspješno poslano.

    Za razvoj: ako TWILIO_ACCOUNT_SID nije postavljen,
    ispisuje OTP u konzolu.
    """
    messages_map = {
        'register': f'RezervišiBiH: Vaš kod za verifikaciju je {otp}. Važi 10 minuta.',
        'login': f'RezervišiBiH: Kod za prijavu je {otp}. Važi 10 minuta.',
        'reset': f'RezervišiBiH: Kod za reset lozinke je {otp}. Važi 10 minuta.',
    }
    message = messages_map.get(purpose, f'Vaš kod je {otp}')

    # Razvojni mod — samo ispiši u konzolu
    if settings.DEBUG and not getattr(settings, 'TWILIO_ACCOUNT_SID', None):
        print(f"\n{'=' * 40}")
        print(f"SMS na {phone}: {message}")
        print(f"{'=' * 40}\n")
        return True

    # --- Twilio ---
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone
        )
        return True
    except Exception as e:
        print(f"Twilio greška: {e}")

    # --- Infobip (fallback, bolji za BiH/region) ---
    # try:
    #     import requests
    #     resp = requests.post(
    #         f"https://{settings.INFOBIP_BASE_URL}/sms/2/text/advanced",
    #         headers={
    #             "Authorization": f"App {settings.INFOBIP_API_KEY}",
    #             "Content-Type": "application/json",
    #         },
    #         json={
    #             "messages": [{
    #                 "from": "RezervišiBiH",
    #                 "destinations": [{"to": phone}],
    #                 "text": message,
    #             }]
    #         }
    #     )
    #     return resp.status_code == 200
    # except Exception as e:
    #     print(f"Infobip greška: {e}")

    return False