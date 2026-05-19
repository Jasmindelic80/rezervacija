import logging
from django.conf import settings

from .channels.viber import ViberNotifier
from .channels.whatsapp import WhatsAppNotifier
from .channels.sms import SMSNotifier
from .models import NotificationLog, NotificationPreference

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Pametan dispatcher koji:
    1. Pita koji kanal korisnik preferira
    2. Pokušava Viber → WhatsApp → SMS
    3. Logira svaki pokušaj
    """

    def __init__(self):
        self.viber = ViberNotifier()
        self.whatsapp = WhatsAppNotifier()
        self.sms = SMSNotifier()

    def send(self, user, message_type: str, context: dict,
             appointment=None) -> bool:
        """
        Pošalji notifikaciju korisniku kroz optimalni kanal.

        Args:
            user: User instanca
            message_type: 'confirmation', 'reminder_24h', 'reminder_2h', 'cancellation'
            context: Dict s podacima za poruku
            appointment: Appointment instanca (opciono)
        """
        if not user.phone:
            logger.warning(f"Korisnik {user} nema broj telefona")
            return False

        # Dohvati preference
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)

        # Provjeri želi li korisnik ovaj tip notifikacije
        pref_map = {
            'confirmation': prefs.receive_confirmation,
            'reminder_24h': prefs.receive_reminder_24h,
            'reminder_2h': prefs.receive_reminder_2h,
            'cancellation': prefs.receive_cancellation,
        }
        if not pref_map.get(message_type, True):
            logger.info(f"Korisnik {user} nije pretplaćen na {message_type}")
            return False

        # Generiši poruku
        message = self._build_message(message_type, context)
        wa_template, wa_components = self._get_wa_template(message_type, context)

        # Redoslijed pokušaja prema preferencama
        channels_order = self._get_channels_order(prefs)

        for channel in channels_order:
            result = self._try_send(channel, user.phone, message,
                                    wa_template, wa_components)
            status = NotificationLog.STATUS_SENT if result['success'] else NotificationLog.STATUS_FAILED
            if not result['success'] and channel != channels_order[-1]:
                status = NotificationLog.STATUS_FALLBACK

            NotificationLog.objects.create(
                appointment=appointment,
                user=user,
                channel=channel,
                message_type=message_type,
                status=status,
                provider_message_id=result.get('message_id', ''),
                error_message=result.get('error', ''),
            )

            if result['success']:
                logger.info(f"Notifikacija {message_type} poslana via {channel} → {user}")
                return True
            else:
                logger.warning(f"{channel} neuspješan: {result.get('error')} — probam sljedeći")

        logger.error(f"Svi kanali neuspješni za {user} [{message_type}]")
        return False

    def _get_channels_order(self, prefs: NotificationPreference) -> list:
        """Redoslijed kanala prema preferencama korisnika"""
        preferred = prefs.preferred_channel
        all_channels = ['viber', 'whatsapp', 'sms']

        # Stavi preferirani prvi, ostali kao fallback
        order = [preferred] + [c for c in all_channels if c != preferred]
        return order

    def _try_send(self, channel: str, phone: str, message: str,
                  wa_template: str = None, wa_components: list = None) -> dict:
        """Pokušaj slanje putem specificiranog kanala"""
        if settings.DEBUG and not getattr(settings, 'INFOBIP_API_KEY', None):
            # Dev mod — ispiši u konzolu
            print(f"\n{'=' * 50}")
            print(f"[DEV] {channel.upper()} → {phone}")
            print(f"Poruka: {message}")
            print(f"{'=' * 50}\n")
            return {'success': True, 'message_id': 'dev_mock_id'}

        if channel == 'viber':
            return self.viber.send_text(phone, message)
        elif channel == 'whatsapp':
            if wa_template:
                return self.whatsapp.send_template(phone, wa_template, components=wa_components)
            return self.whatsapp.send_text(phone, message)
        elif channel == 'sms':
            return self.sms.send(phone, message)
        return {'success': False, 'error': f'Nepoznat kanal: {channel}'}

    def _build_message(self, message_type: str, ctx: dict) -> str:
        """Generiši tekst poruke"""
        name = ctx.get('client_name', 'Poštovani')
        business = ctx.get('business_name', '')
        date = ctx.get('date', '')
        time = ctx.get('time', '')
        service = ctx.get('service_name', '')
        staff = ctx.get('staff_name', '')
        cancel_url = ctx.get('cancel_url', '')

        staff_text = f" (sa {staff})" if staff else ""

        templates = {
            'confirmation': (
                f"✅ *RezervišiBiH* — Potvrda termina\n\n"
                f"Zdravo {name}!\n\n"
                f"Vaš termin je potvrđen:\n"
                f"📍 *{business}*\n"
                f"🔧 {service}{staff_text}\n"
                f"📅 {date} u {time}\n\n"
                f"Za otkazivanje (min. 2h unaprijed):\n{cancel_url}"
            ),
            'reminder_24h': (
                f"⏰ *Podsjetnik* — sutra imate termin!\n\n"
                f"Zdravo {name}, podsjećamo vas:\n\n"
                f"📍 *{business}*\n"
                f"🔧 {service}{staff_text}\n"
                f"📅 Sutra u {time}\n\n"
                f"Vidimo se! 😊"
            ),
            'reminder_2h': (
                f"🔔 Vaš termin je za 2 sata!\n\n"
                f"📍 *{business}*\n"
                f"🕐 Danas u {time}\n\n"
                f"Ne zaboravite! 💪"
            ),
            'cancellation': (
                f"❌ Termin otkazan\n\n"
                f"Zdravo {name}, vaš termin u *{business}* "
                f"({date} u {time}) je otkazan.\n\n"
                f"Rezervišite novi termin: rezervisi.ba"
            ),
            'cancellation_by_business': (
                f"⚠️ Važna obavijest\n\n"
                f"Zdravo {name},\n"
                f"*{business}* je otkazao vaš termin "
                f"({date} u {time}) zbog nepredviđenih okolnosti.\n\n"
                f"Izvinjavamo se na neugodnosti. "
                f"Rezervišite novi termin: rezervisi.ba"
            ),
        }
        return templates.get(message_type, f"Obavijest od RezervišiBiH")

    def _get_wa_template(self, message_type: str, ctx: dict):
        """
        WhatsApp template nazivi i komponente.
        Ove template treba kreirati i odobriti na
        Meta Business Manager > WhatsApp Manager > Message Templates
        """
        wa_templates = {
            'confirmation': (
                'rezervisi_potvrda',  # Naziv template na Meta
                [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": ctx.get('client_name', '')},
                        {"type": "text", "text": ctx.get('business_name', '')},
                        {"type": "text", "text": ctx.get('service_name', '')},
                        {"type": "text", "text": ctx.get('date', '')},
                        {"type": "text", "text": ctx.get('time', '')},
                        {"type": "text", "text": ctx.get('cancel_url', '')},
                    ]
                }]
            ),
            'reminder_24h': (
                'rezervisi_podsjetnik_24h',
                [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": ctx.get('client_name', '')},
                        {"type": "text", "text": ctx.get('business_name', '')},
                        {"type": "text", "text": ctx.get('time', '')},
                    ]
                }]
            ),
            'reminder_2h': (
                'rezervisi_podsjetnik_2h',
                [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": ctx.get('business_name', '')},
                        {"type": "text", "text": ctx.get('time', '')},
                    ]
                }]
            ),
            'cancellation': ('rezervisi_otkaz', []),
        }
        return wa_templates.get(message_type, (None, None))


# Singleton instanca
dispatcher = NotificationDispatcher()

