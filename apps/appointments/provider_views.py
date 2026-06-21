import calendar as cal_module
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from datetime import date, datetime, timedelta

from apps.businesses.models import Business, Staff
from apps.services.models import Service
from apps.availability.models import WorkingHours, BlockedSlot, DAYS_OF_WEEK
from .models import Appointment


def _get_provider_business(request, slug):
    """Vrati biznis ako je current user njegov vlasnik."""
    return get_object_or_404(Business, slug=slug, owner=request.user)


def _provider_context(request):
    """Zajednički context za provider sidebar."""
    businesses = Business.objects.filter(owner=request.user, is_active=True)
    return {'businesses': businesses}


@login_required
def provider_dashboard(request):
    if not request.user.is_provider():
        return HttpResponseForbidden()

    today = date.today()
    from django.db.models import Count, Q

    businesses = Business.objects.filter(owner=request.user, is_active=True).annotate(
        today_confirmed=Count(
            'appointments',
            filter=Q(
                appointments__start_datetime__date=today,
                appointments__status=Appointment.STATUS_CONFIRMED,
            )
        ),
        pending_count=Count(
            'appointments',
            filter=Q(appointments__status=Appointment.STATUS_PENDING)
        ),
    )

    today_appointments = Appointment.objects.filter(
        business__in=businesses,
        start_datetime__date=today,
    ).select_related('client', 'service', 'staff').order_by('start_datetime')

    ctx = _provider_context(request)
    ctx.update({
        'businesses': businesses,
        'today_appointments': today_appointments,
        'today': today,
    })
    return render(request, 'provider/dashboard.html', ctx)


@login_required
def provider_appointments(request, slug):
    business = _get_provider_business(request, slug)

    qs = Appointment.objects.filter(business=business).select_related('client', 'service', 'staff')

    filter_od = request.GET.get('od', '')
    filter_do = request.GET.get('do', '')
    filter_status = request.GET.get('status', '')

    if filter_od:
        qs = qs.filter(start_datetime__date__gte=filter_od)
    if filter_do:
        qs = qs.filter(start_datetime__date__lte=filter_do)
    if filter_status:
        qs = qs.filter(status=filter_status)

    if not filter_od and not filter_do:
        qs = qs.filter(start_datetime__date__gte=date.today() - timedelta(days=7))

    qs = qs.order_by('start_datetime')

    ctx = _provider_context(request)
    ctx.update({
        'business': business,
        'active_business': business,
        'appointments': qs,
        'filter_od': filter_od,
        'filter_do': filter_do,
        'filter_status': filter_status,
    })
    return render(request, 'provider/appointments.html', ctx)


@login_required
def provider_appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment, pk=pk, business__owner=request.user
    )
    ctx = _provider_context(request)
    ctx.update({
        'appointment': appointment,
        'active_business': appointment.business,
    })
    return render(request, 'provider/appointment_detail.html', ctx)


@login_required
def provider_appointment_action(request, pk):
    if request.method != 'POST':
        return redirect('provider_dashboard')

    appointment = get_object_or_404(
        Appointment, pk=pk, business__owner=request.user
    )
    action = request.POST.get('action')

    if action == 'confirm' and appointment.status == Appointment.STATUS_PENDING:
        appointment.status = Appointment.STATUS_CONFIRMED
        appointment.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Termin je potvrđen.')

    elif action == 'complete' and appointment.status == Appointment.STATUS_CONFIRMED:
        appointment.status = Appointment.STATUS_COMPLETED
        appointment.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Termin označen kao završen.')

    elif action == 'no_show' and appointment.status == Appointment.STATUS_CONFIRMED:
        appointment.status = Appointment.STATUS_NO_SHOW
        appointment.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Termin označen — klijent se nije pojavio.')

    elif action == 'cancel':
        reason = request.POST.get('reason', '')
        appointment.status = Appointment.STATUS_CANCELLED_BUSINESS
        appointment.cancellation_reason = reason
        appointment.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
        messages.success(request, 'Termin je otkazan.')

    elif action == 'note':
        appointment.internal_notes = request.POST.get('internal_notes', '')
        appointment.save(update_fields=['internal_notes', 'updated_at'])
        messages.success(request, 'Napomena sačuvana.')

    return redirect('provider_appointment_detail', pk=pk)


@login_required
def provider_appointment_create(request, slug):
    business = _get_provider_business(request, slug)
    services = Service.objects.filter(business=business, is_active=True)
    staff_list = Staff.objects.filter(business=business, is_active=True)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    clients = User.objects.filter(role='client').order_by('first_name', 'username')

    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        staff_id = request.POST.get('staff_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        client_id = request.POST.get('client_id')
        client_name = request.POST.get('client_name', '').strip()
        notes = request.POST.get('notes', '')

        try:
            service = Service.objects.get(id=service_id, business=business)
            selected_date = date.fromisoformat(date_str)
            selected_time = datetime.strptime(time_str, '%H:%M').time()
            start_dt = datetime.combine(selected_date, selected_time)
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)

            staff = None
            if staff_id:
                staff = Staff.objects.filter(id=staff_id, business=business).first()

            # Provjeri radno vrijeme
            wh_qs = WorkingHours.objects.filter(
                business=business,
                day_of_week=selected_date.weekday(),
                is_closed=False,
            )
            wh = (wh_qs.filter(staff=staff).first() or wh_qs.filter(staff__isnull=True).first()) if staff else wh_qs.filter(staff__isnull=True).first()
            if wh:
                if not (wh.open_time <= selected_time < wh.close_time):
                    messages.error(request, f'Termin mora biti unutar radnog vremena ({wh.open_time.strftime("%H:%M")}–{wh.close_time.strftime("%H:%M")}).')
                    raise ValueError('Van radnog vremena')
            else:
                messages.error(request, 'Salon tog dana ne radi.')
                raise ValueError('Neradni dan')

            client = None
            if client_id:
                client = User.objects.filter(id=client_id).first()

            if not client:
                client, _ = User.objects.get_or_create(
                    username=f'walk_in_{client_name.lower().replace(" ", "_")}_{start_dt.strftime("%Y%m%d%H%M")}',
                    defaults={
                        'first_name': client_name or 'Walk-in',
                        'role': 'client',
                    }
                )

            Appointment.objects.create(
                client=client,
                business=business,
                service=service,
                staff=staff,
                start_datetime=timezone.make_aware(start_dt),
                end_datetime=timezone.make_aware(end_dt),
                internal_notes=notes,
                status=Appointment.STATUS_CONFIRMED,
            )
            messages.success(request, 'Termin je kreiran.')
            return redirect('provider_appointments', slug=slug)

        except Exception as e:
            messages.error(request, f'Greška: {e}')

    ctx = _provider_context(request)
    ctx.update({
        'business': business,
        'active_business': business,
        'services': services,
        'staff_list': staff_list,
        'clients': clients,
        'today': date.today().isoformat(),
    })
    return render(request, 'provider/appointment_create.html', ctx)


@login_required
def provider_working_hours(request, slug):
    business = _get_provider_business(request, slug)

    if request.method == 'POST':
        for day_num, day_name in DAYS_OF_WEEK:
            is_closed = bool(request.POST.get(f'closed_{day_num}'))
            open_time = request.POST.get(f'open_{day_num}') or None
            close_time = request.POST.get(f'close_{day_num}') or None

            WorkingHours.objects.update_or_create(
                business=business,
                staff=None,
                day_of_week=day_num,
                defaults={
                    'is_closed': is_closed,
                    'open_time': None if is_closed else open_time,
                    'close_time': None if is_closed else close_time,
                }
            )
        messages.success(request, 'Radno vrijeme je sačuvano.')
        return redirect('provider_working_hours', slug=slug)

    existing = {wh.day_of_week: wh for wh in
                WorkingHours.objects.filter(business=business, staff__isnull=True)}

    days = []
    for day_num, day_name in DAYS_OF_WEEK:
        wh = existing.get(day_num)
        days.append({
            'day': day_num,
            'name': day_name,
            'is_closed': wh.is_closed if wh else (day_num >= 6),
            'open_time': wh.open_time.strftime('%H:%M') if wh and wh.open_time else '09:00',
            'close_time': wh.close_time.strftime('%H:%M') if wh and wh.close_time else '17:00',
        })

    ctx = _provider_context(request)
    ctx.update({
        'business': business,
        'active_business': business,
        'days': days,
    })
    return render(request, 'provider/working_hours.html', ctx)


@login_required
def provider_blocked_slots(request, slug):
    business = _get_provider_business(request, slug)
    staff_list = Staff.objects.filter(business=business, is_active=True)

    if request.method == 'POST':
        start_str = request.POST.get('start_datetime')
        end_str = request.POST.get('end_datetime')
        reason = request.POST.get('reason', '')
        staff_id = request.POST.get('staff_id')

        try:
            start_dt = timezone.make_aware(datetime.fromisoformat(start_str))
            end_dt = timezone.make_aware(datetime.fromisoformat(end_str))

            if end_dt <= start_dt:
                messages.error(request, 'Kraj mora biti nakon početka.')
            else:
                staff = None
                if staff_id:
                    staff = Staff.objects.filter(id=staff_id, business=business).first()

                BlockedSlot.objects.create(
                    business=business,
                    staff=staff,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    reason=reason,
                )
                messages.success(request, 'Blokada je dodana.')
        except Exception as e:
            messages.error(request, f'Greška: {e}')

        return redirect('provider_blocked_slots', slug=slug)

    blocked_slots = BlockedSlot.objects.filter(
        business=business,
        end_datetime__gte=timezone.now(),
    ).select_related('staff').order_by('start_datetime')

    ctx = _provider_context(request)
    ctx.update({
        'business': business,
        'active_business': business,
        'staff_list': staff_list,
        'blocked_slots': blocked_slots,
    })
    return render(request, 'provider/blocked_slots.html', ctx)


@login_required
def provider_blocked_slot_delete(request, pk):
    slot = get_object_or_404(BlockedSlot, pk=pk, business__owner=request.user)
    if request.method == 'POST':
        slug = slot.business.slug
        slot.delete()
        messages.success(request, 'Blokada je obrisana.')
        return redirect('provider_blocked_slots', slug=slug)
    return redirect('provider_dashboard')


@login_required
def provider_calendar(request, slug):
    business = _get_provider_business(request, slug)

    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Granice mjeseca
    first_day = date(year, month, 1)
    last_day = date(year, month, cal_module.monthrange(year, month)[1])

    # Svi termini u tom mjesecu
    appts = Appointment.objects.filter(
        business=business,
        start_datetime__date__gte=first_day,
        start_datetime__date__lte=last_day,
    ).values('start_datetime__date', 'status')

    # Broji po danu i statusu
    from collections import defaultdict
    day_counts = defaultdict(lambda: {'total': 0, 'pending': 0, 'confirmed': 0, 'cancelled': 0})
    for a in appts:
        d = a['start_datetime__date']
        day_counts[d]['total'] += 1
        s = a['status']
        if s == Appointment.STATUS_PENDING:
            day_counts[d]['pending'] += 1
        elif s == Appointment.STATUS_CONFIRMED:
            day_counts[d]['confirmed'] += 1
        elif s in (Appointment.STATUS_CANCELLED_CLIENT, Appointment.STATUS_CANCELLED_BUSINESS):
            day_counts[d]['cancelled'] += 1

    # Gradi kalendar matricu (sedmice)
    cal = cal_module.monthcalendar(year, month)

    # Prev / next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_names = [
        '', 'Januar', 'Februar', 'Mart', 'April', 'Maj', 'Juni',
        'Juli', 'August', 'Septembar', 'Oktobar', 'Novembar', 'Decembar'
    ]

    ctx = _provider_context(request)
    if (year, month) < (today.year, today.month):
        past_threshold = 33  # cijeli prošli mjesec
    elif (year, month) == (today.year, today.month):
        past_threshold = today.day  # dani prije danas
    else:
        past_threshold = 0  # budući mjesec, ništa sivo

    ctx.update({
        'business': business,
        'active_business': business,
        'calendar': cal,
        'day_counts': dict(day_counts),
        'year': year,
        'month': month,
        'month_name': month_names[month],
        'today': today,
        'past_threshold': past_threshold,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
    })
    return render(request, 'provider/calendar.html', ctx)


@login_required
def provider_calendar_day(request, slug):
    """AJAX — termini za određeni dan."""
    business = _get_provider_business(request, slug)
    date_str = request.GET.get('date', '')

    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Pogrešan datum'}, status=400)

    appts = Appointment.objects.filter(
        business=business,
        start_datetime__date=target,
    ).select_related('client', 'service', 'staff').order_by('start_datetime')

    data = []
    for a in appts:
        data.append({
            'id': str(a.pk),
            'time': a.start_datetime.strftime('%H:%M'),
            'end_time': a.end_datetime.strftime('%H:%M'),
            'client': a.client.get_full_name() or a.client.username,
            'service': a.service.name if a.service else '—',
            'staff': a.staff.name if a.staff else '—',
            'status': a.status,
            'status_display': a.get_status_display(),
            'url': f'/termin/termin/{a.pk}/',
        })

    # Slobodni termini (samo za danas i buduće dane)
    from apps.availability.utils import get_available_slots
    from apps.services.models import Service
    is_past = target < date.today()
    free_slots = []
    if not is_past:
        first_service = Service.objects.filter(business=business, is_active=True).first()
        if first_service:
            slots = get_available_slots(business, first_service, target_date=target)
            free_slots = [s.strftime('%H:%M') for s in slots]

    return JsonResponse({
        'date': date_str,
        'appointments': data,
        'free_slots': free_slots,
        'is_past': is_past,
    })
