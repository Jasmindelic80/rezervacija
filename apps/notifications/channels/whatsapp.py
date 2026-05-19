import httpx
from django.conf import settings


class WhatsAppNotifier:
    """
    Meta WhatsApp Cloud API (besplatno do 1000 konverzacija/mjesec)
    Docs: https://developers.facebook.com/docs/whatsapp/cloud-api

    Alternativa: Infobip WhatsApp (isti account kao Viber, lakše upravljanje)

    VAŽNO: WhatsApp zahtijeva pre-odobrene template poruke za
    business-initiated poruke (notifikacije). Treba aplicirati
    template na Meta Business Manageru.
    """
    API_URL = "https://graph.facebook.com/v18.0/{phone_id}/messages"

    def __init__(self):
        self.token = settings.WHATSAPP_TOKEN  # Meta access token
        self.phone_id = settings.WHATSAPP_PHONE_ID  # WhatsApp Business phone ID

    def send_template(self, to_phone: str, template_name: str,
                      language: str = 'bs', components: list = None) -> dict:
        """
        Pošalji pre-odobreni template.

        Primjer template 'appointment_confirmation':
        "Poštovani {{1}}, Vaš termin u {{2}} je potvrđen za {{3}} u {{4}}.
         Za otkazivanje: {{5}}"
        """
        url = self.API_URL.format(phone_id=self.phone_id)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or []
            }
        }
        try:
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10.0
            )
            data = resp.json()
            if resp.status_code == 200:
                return {'success': True, 'message_id': data.get('messages', [{}])[0].get('id')}
            return {'success': False, 'error': str(data)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def send_text(self, to_phone: str, message: str) -> dict:
        """
        Slobodan tekst — moguć SAMO ako je korisnik u zadnjih 24h
        kontaktirao business (customer-initiated window).
        Za notifikacije van prozora koristiti template!
        """
        url = self.API_URL.format(phone_id=self.phone_id)
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message}
        }
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json=payload, timeout=10.0
            )
            data = resp.json()
            return {'success': resp.status_code == 200, 'data': data}
        except Exception as e:
            return {'success': False, 'error': str(e)}

