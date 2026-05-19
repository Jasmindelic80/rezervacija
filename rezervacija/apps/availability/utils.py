from datetime import datetime, timedelta, date, time
from django.utils import timezone
from apps.appointments.models import Appointment
from .models import WorkingHours, BlockedSlot


def get_available_slots(business, service, staff=None, target_date=None):
    """
    Vraća listu slobodnih datetime termina za dati dan.

    Args:
        business: Business instanca
        service: Service instanca (koristi duration_minutes)
        staff: Staff instanca (opciono)
        target_date: datetime.date objekt

    Returns:
        Lista datetime objekata koji su slobodni
    """
    if target_date is None:
        target_date = date.today()

    # Ne prikazuj termine u prošlosti
    now = timezone.localtime(timezone.now())

    duration = timedelta(minutes=service.duration_minutes)
    day_of_week = target_date.weekday()
    interval = timedelta(minutes=business.appointment_interval_minutes)

    # 1. Provjeri radno vrijeme
    wh_qs = WorkingHours.objects.filter(
        business=business,
        day_of_week=day_of_week,
        is_closed=False
    )
    if staff:
        # Prioritet: radno vrijeme specifičnog radnika, inače biznisa
        staff_wh = wh_qs.filter(staff=staff).first()
        business_wh = wh_qs.filter(staff__isnull=True).first()
        working_hours = staff_wh or business_wh
    else:
        working_hours = wh_qs.filter(staff__isnull=True).first()

    if not working_hours:
        return []

    # 2. Generiši sve potencijalne termine
    day_start = datetime.combine(target_date, working_hours.open_time)
    day_end = datetime.combine(target_date, working_hours.close_time)

    # Ako je danas, ne prikazuj prošle termine
    if target_date == now.date():
        earliest = now + timedelta(minutes=30)  # Minimum 30 min unaprijed
        if earliest > day_end:
            return []
        day_start = max(day_start, earliest.replace(second=0, microsecond=0))

    all_slots = []
    current = day_start
    while current + duration <= day_end:
        all_slots.append(current)
        current += interval

    if not all_slots:
        return []

    # 3. Dohvati postojeće rezervacije
    appt_qs = Appointment.objects.filter(
        business=business,
        start_datetime__date=target_date,
        status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
    )
    if staff:
        appt_qs = appt_qs.filter(staff=staff)

    # 4. Dohvati blokirane termine
    blocked_qs = BlockedSlot.objects.filter(
        business=business,
        start_datetime__date=target_date
    )
    if staff:
        blocked_qs = blocked_qs.filter(staff=staff)

    # 5. Filtriraj slobodne termine
    def overlaps(slot_start, slot_end, range_start, range_end):
        return not (slot_end <= range_start or slot_start >= range_end)

    available = []
    for slot in all_slots:
        slot_end = slot + duration

        # Provjeri rezervacije
        booked = any(
            overlaps(slot, slot_end, a.start_datetime.replace(tzinfo=None),
                     a.end_datetime.replace(tzinfo=None))
            for a in appt_qs
        )
        if booked:
            continue

        # Provjeri blokade
        blocked = any(
            overlaps(slot, slot_end, b.start_datetime.replace(tzinfo=None),
                     b.end_datetime.replace(tzinfo=None))
            for b in blocked_qs
        )
        if blocked:
            continue

        available.append(slot)

    return available


def get_next_available_date(business, service, staff=None, days_ahead=30):
    """
    Vraća datum sljedećeg slobodnog termina.
    Korisno za prikaz na listi biznisa.
    """
    check_date = date.today()
    for _ in range(days_ahead):
        slots = get_available_slots(business, service, staff, check_date)
        if slots:
            return check_date, slots[0]
        check_date += timedelta(days=1)
    return None, None


def get_week_availability(business, service, staff=None, start_date=None):
    """
    Vraća dostupnost za 7 dana (za kalendarski prikaz).
    Returns: dict {date: [slots]}
    """
    if start_date is None:
        start_date = date.today()

    week = {}
    for i in range(7):
        day = start_date + timedelta(days=i)
        week[day] = get_available_slots(business, service, staff, day)
    return week
