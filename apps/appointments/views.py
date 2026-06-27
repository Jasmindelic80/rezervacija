
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, date, timedelta

from apps.businesses.models import Business, Staff
from apps.services.models import Service
from apps.availability.utils import get_available_slots
from .models import Appointment


@login_required
def book_appointment(request, business_slug):
    business = get_object_or_404(Business, slug=business_slug, is_active=True)
    services = business.services.filter(is_active=True)
    staff_list = business.staff.filter(is_active=True)

    if request.method == 'POST':
        service_id = request.POST.get('service_id')
        staff_id = request.POST.get('staff_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        notes = request.POST.get('notes', '')

        try:
            service = Service.objects.get(id=service_id, business=business)
            selected_date = date.fromisoformat(date_str)
            selected_time = datetime.strptime(time_str, '%H:%M').time()
            start_dt = datetime.combine(selected_date, selected_time)

            staff = None
            if staff_id and staff_id != 'any':
                staff = Staff.objects.get(id=staff_id, business=business)

            # Provjeri je li termin još uvijek slobodan
            available = get_available_slots(business, service, staff, selected_date)
            slot_times = [s.strftime('%H:%M') for s in available]

            if time_str not in slot_times:
                messages.error(request, 'Ovaj termin više nije slobodan. Molimo odaberite drugi.')
                return redirect('book', business_slug=business_slug)

            end_dt = start_dt + timedelta(minutes=service.duration_minutes)

            appointment = Appointment.objects.create(
                client=request.user,
                business=business,
                service=service,
                staff=staff,
                start_datetime=timezone.make_aware(start_dt),
                end_datetime=timezone.make_aware(end_dt),
                client_notes=notes,
                status=Appointment.STATUS_CONFIRMED
            )

            messages.success(
                request,
                f'Termin uspješno rezervisan! {appointment.start_datetime:%d.%m.%Y u %H:%M}'
            )

            try:
                from apps.notifications.tasks import _send_email
                _send_email(appointment, 'confirmation')
            except Exception:
                pass

            return redirect('appointment_confirm', pk=appointment.pk)

        except Exception as e:
            messages.error(request, f'Greška pri rezervaciji: {e}')

    context = {
        'business': business,
        'services': services,
        'staff_list': staff_list,
        'today': date.today().isoformat(),
        'max_date': (date.today() + timedelta(days=60)).isoformat(),
    }
    return render(request, 'appointments/book.html', context)


@login_required
def appointment_confirm(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)
    from apps.notifications.tasks import _google_calendar_url
    return render(request, 'appointments/confirm.html', {
        'appointment': appointment,
        'google_cal_url': _google_calendar_url(appointment),
    })


@login_required
def my_appointments(request):
    upcoming = Appointment.objects.filter(
        client=request.user,
        start_datetime__gte=timezone.now(),
        status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED]
    ).select_related('business', 'service', 'staff')

    past = Appointment.objects.filter(
        client=request.user,
        start_datetime__lt=timezone.now()
    ).select_related('business', 'service')[:20]

    context = {
        'upcoming': upcoming,
        'past': past,
    }
    return render(request, 'appointments/my_appointments.html', context)


@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)

    if not appointment.is_cancellable():
        messages.error(
            request,
            'Ovaj termin se ne može otkazati. '
            'Možete otkazati termin najmanje 2 sata unaprijed.'
        )
        return redirect('my_appointments')

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        appointment.status = Appointment.STATUS_CANCELLED_CLIENT
        appointment.cancellation_reason = reason
        appointment.save()

        messages.success(request, 'Termin je uspješno otkazan.')

        try:
            from apps.notifications.tasks import _send_email
            _send_email(appointment, 'cancellation')
        except Exception:
            pass
        return redirect('my_appointments')

    return render(request, 'appointments/cancel.html', {'appointment': appointment})


def appointment_ics(request, pk):
    """Generiši .ics fajl za dodavanje termina u kalendar."""
    appointment = get_object_or_404(Appointment, pk=pk)

    start = appointment.start_datetime.astimezone(timezone.utc)
    end = appointment.end_datetime.astimezone(timezone.utc)
    dt_fmt = '%Y%m%dT%H%M%SZ'
    now_fmt = timezone.now().strftime(dt_fmt)

    service_name = appointment.service.name if appointment.service else 'Termin'
    staff_text = f' sa {appointment.staff.name}' if appointment.staff else ''
    location = f'{appointment.business.address}, {appointment.business.city}' if appointment.business.address else appointment.business.city
    description = f'{service_name}{staff_text} — {appointment.business.name}'

    ics = (
        'BEGIN:VCALENDAR\r\n'
        'VERSION:2.0\r\n'
        'PRODID:-//RezervišiBiH//HR\r\n'
        'CALSCALE:GREGORIAN\r\n'
        'METHOD:PUBLISH\r\n'
        'BEGIN:VEVENT\r\n'
        f'UID:{appointment.pk}@rezervisi.ba\r\n'
        f'DTSTAMP:{now_fmt}\r\n'
        f'DTSTART:{start.strftime(dt_fmt)}\r\n'
        f'DTEND:{end.strftime(dt_fmt)}\r\n'
        f'SUMMARY:{service_name} — {appointment.business.name}\r\n'
        f'DESCRIPTION:{description}\r\n'
        f'LOCATION:{location}\r\n'
        'END:VEVENT\r\n'
        'END:VCALENDAR\r\n'
    )

    response = HttpResponse(ics, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="termin-{start.strftime("%Y%m%d-%H%M")}.ics"'
    return response


@login_required
def reschedule_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)

    if not appointment.is_reschedulable():
        messages.error(
            request,
            'Ovaj termin se ne može promijeniti. '
            'Možete mijenjati termin najmanje 2 sata unaprijed.'
        )
        return redirect('my_appointments')

    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')

        try:
            selected_date = date.fromisoformat(date_str)
            selected_time = datetime.strptime(time_str, '%H:%M').time()
            start_dt = datetime.combine(selected_date, selected_time)

            available = get_available_slots(
                appointment.business, appointment.service, appointment.staff, selected_date
            )
            slot_times = [s.strftime('%H:%M') for s in available]

            if time_str not in slot_times:
                messages.error(request, 'Ovaj termin više nije slobodan. Odaberite drugi.')
                return redirect('reschedule', pk=pk)

            duration = timedelta(minutes=appointment.service.duration_minutes)
            appointment.start_datetime = timezone.make_aware(start_dt)
            appointment.end_datetime = timezone.make_aware(start_dt) + duration
            appointment.save(update_fields=['start_datetime', 'end_datetime', 'updated_at'])

            messages.success(
                request,
                f'Termin je uspješno premješten na {appointment.start_datetime:%d.%m.%Y u %H:%M}.'
            )
            return redirect('my_appointments')

        except Exception as e:
            messages.error(request, f'Greška: {e}')

    context = {
        'appointment': appointment,
        'today': date.today().isoformat(),
        'max_date': (date.today() + timedelta(days=60)).isoformat(),
    }
    return render(request, 'appointments/reschedule.html', context)