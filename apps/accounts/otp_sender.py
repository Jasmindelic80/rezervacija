"""
Slanje OTP kodova putem SMS, Viber ili WhatsApp (Infobip).
U DEBUG modu bez konfiguriranog Infobipa — ispisuje kod u konzolu.
"""
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

MESSAGES = {
    'register': 'BookBiH: Vaš kod za verifikaciju je {otp}. Važi 10 minuta.',
    'login':    'BookBiH: Kod za prijavu je {otp}. Važi 10 minuta.',
    'reset':    'BookBiH: Kod za reset lozinke je {otp}. Važi 10 minuta.',
}

EMAIL_SUBJECTS = {
    'register': 'BookBiH — Verifikacijski kod',
    'login':    'BookBiH — Kod za prijavu',
    'reset':    'BookBiH — Kod za reset lozinke',
}


def send_otp_email(email: str, otp: str, purpose: str = 'register') -> bool:
    message = MESSAGES.get(purpose, f'Vaš kod je {otp}').format(otp=otp)
    subject = EMAIL_SUBJECTS.get(purpose, 'BookBiH — Kod')
    body = (
        f"{message}\n\n"
        f"Kod je: {otp}\n\n"
        f"Kod važi 10 minuta. Ako niste tražili ovaj kod, ignorišite poruku.\n\n"
        f"— Tim BookBiH"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'BookBiH <terminbih@gmail.com>'),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"Email OTP poslan na {email}")
        return True
    except Exception as e:
        logger.error(f"Email OTP greška: {e}")
        return False


def send_otp(phone: str, otp: str, channel: str = 'sms', purpose: str = 'register') -> bool:
    """
    Pošalji OTP kod na telefon putem odabranog kanala.
    channel: 'sms' | 'viber' | 'whatsapp'
    Vraća True ako je uspješno poslano.
    """
    message = MESSAGES.get(purpose, f'Vaš kod je {otp}').format(otp=otp)
    api_key = getattr(settings, 'INFOBIP_API_KEY', '')
    base_url = getattr(settings, 'INFOBIP_BASE_URL', '')
    has_infobip = bool(api_key and base_url)
    has_meta_wa = bool(
        getattr(settings, 'WHATSAPP_TOKEN', '') and
        getattr(settings, 'WHATSAPP_PHONE_ID', '')
    )

    # DEV mod — ispiši u konzolu ako nema potrebnih kredencijala
    if channel == 'whatsapp' and not has_meta_wa and not has_infobip:
        logger.warning(f"[DEV OTP] WHATSAPP → {phone} | Kod: {otp} | Svrha: {purpose}")
        print(f"\n{'='*50}\n  OTP KOD (WHATSAPP): {otp}\n  Broj: {phone}\n{'='*50}\n")
        return True
    if channel != 'whatsapp' and not has_infobip:
        logger.warning(f"[DEV OTP] {channel.upper()} → {phone} | Kod: {otp} | Svrha: {purpose}")
        print(f"\n{'='*50}\n  OTP KOD ({channel.upper()}): {otp}\n  Broj: {phone}\n{'='*50}\n")
        return True

    infobip_headers = {
        'Authorization': f'App {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    try:
        if channel == 'sms':
            return _send_sms(phone, message, base_url, infobip_headers)
        elif channel == 'viber':
            ok = _send_viber(phone, message, base_url, infobip_headers)
            if not ok:
                logger.info("Viber neuspješan, fallback na SMS")
                return _send_sms(phone, message, base_url, infobip_headers)
            return ok
        elif channel == 'whatsapp':
            ok = _send_whatsapp(phone, otp)
            if not ok and has_infobip:
                logger.info("WhatsApp neuspješan, fallback na SMS")
                return _send_sms(phone, message, base_url, infobip_headers)
            return ok
        else:
            return _send_sms(phone, message, base_url, infobip_headers)
    except Exception as e:
        logger.error(f"OTP greška ({channel}): {e}")
        return False


def _send_sms(phone: str, message: str, base_url: str, headers: dict) -> bool:
    resp = requests.post(
        f'https://{base_url}/sms/2/text/advanced',
        headers=headers,
        json={
            'messages': [{
                'from': 'RezerviBiH',
                'destinations': [{'to': phone}],
                'text': message,
            }]
        },
        timeout=10,
    )
    if resp.status_code == 200:
        logger.info(f"SMS OTP poslan na {phone}")
        return True
    logger.error(f"Infobip SMS greška {resp.status_code}: {resp.text}")
    return False


def _send_viber(phone: str, message: str, base_url: str, headers: dict) -> bool:
    sender = getattr(settings, 'VIBER_SENDER_NAME', 'BookBiH')
    resp = requests.post(
        f'https://{base_url}/viber/2/messages',
        headers=headers,
        json={
            'to': phone,
            'from': sender,
            'text': message,
        },
        timeout=10,
    )
    if resp.status_code in (200, 201):
        logger.info(f"Viber OTP poslan na {phone}")
        return True
    logger.warning(f"Infobip Viber greška {resp.status_code}: {resp.text}")
    return False


def _send_whatsapp(phone: str, otp: str) -> bool:
    """
    WhatsApp OTP putem Meta Cloud API.
    Template 'rezervisi_otp' mora biti kreiran i odobren na Meta Business Manager.
    """
    token = getattr(settings, 'WHATSAPP_TOKEN', '')
    phone_id = getattr(settings, 'WHATSAPP_PHONE_ID', '')
    if not token or not phone_id:
        return False

    resp = requests.post(
        f'https://graph.facebook.com/v18.0/{phone_id}/messages',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        json={
            'messaging_product': 'whatsapp',
            'to': phone,
            'type': 'template',
            'template': {
                'name': 'rezervisi_otp',
                'language': {'code': 'bs'},
                'components': [
                    {
                        'type': 'body',
                        'parameters': [{'type': 'text', 'text': otp}],
                    }
                ],
            },
        },
        timeout=10,
    )
    if resp.status_code in (200, 201):
        logger.info(f"WhatsApp OTP poslan na {phone}")
        return True
    logger.warning(f"Meta WhatsApp greška {resp.status_code}: {resp.text}")
    return False
