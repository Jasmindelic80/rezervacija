import httpx
from django.conf import settings


class SMSNotifier:
    """Twilio SMS kao krajnji fallback"""

    def send(self, phone: str, message: str) -> dict:
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            msg = client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM_NUMBER,
                to=phone
            )
            return {'success': True, 'message_id': msg.sid}
        except Exception as e:
            return {'success': False, 'error': str(e)}
