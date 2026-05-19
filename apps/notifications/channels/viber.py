import httpx
from django.conf import settings


class ViberNotifier:
    """
    Infobip Viber Business Messages API
    Docs: https://www.infobip.com/docs/viber

    Prednosti za BiH: Viber ima 90%+ penetraciju, besplatno za korisnike
    Cijena: ~0.01-0.03€ po poruci (Infobip)
    """
    BASE_URL = "https://{base_url}/viber/2/messages"

    def __init__(self):
        self.api_key = settings.INFOBIP_API_KEY
        self.base_url = settings.INFOBIP_BASE_URL  # npr. 'xxxxx.api.infobip.com'
        self.sender = settings.VIBER_SENDER_NAME  # npr. 'RezervišiBiH'

    def send_text(self, phone: str, message: str) -> dict:
        """Pošalji text poruku putem Vibera"""
        url = self.BASE_URL.format(base_url=self.base_url)
        payload = {
            "messages": [{
                "from": self.sender,
                "destinations": [{"to": phone}],
                "viber": {
                    "text": message,
                    # "imageUrl": "...",  # Opcionalno — logo biznisa
                    # "buttonText": "Vidi termin",
                    # "buttonUrl": "https://rezervisi.ba/termini/",
                }
            }]
        }
        try:
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"App {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10.0
            )
            data = resp.json()
            if resp.status_code == 200:
                msg_id = data.get('messages', [{}])[0].get('messageId', '')
                return {'success': True, 'message_id': msg_id}
            return {'success': False, 'error': str(data)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def send_with_button(self, phone: str, text: str, btn_text: str, btn_url: str) -> dict:
        """Viber poruka s dugmetom (npr. 'Vidi termin')"""
        url = self.BASE_URL.format(base_url=self.base_url)
        payload = {
            "messages": [{
                "from": self.sender,
                "destinations": [{"to": phone}],
                "viber": {
                    "text": text,
                    "buttonText": btn_text,
                    "buttonUrl": btn_url,
                }
            }]
        }
        try:
            resp = httpx.post(
                url,
                headers={"Authorization": f"App {self.api_key}", "Content-Type": "application/json"},
                json=payload, timeout=10.0
            )
            data = resp.json()
            return {'success': resp.status_code == 200, 'data': data}
        except Exception as e:
            return {'success': False, 'error': str(e)}

