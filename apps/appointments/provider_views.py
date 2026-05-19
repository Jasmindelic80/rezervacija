from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date, timedelta

from apps.businesses.models import Business
from .models import Appointment


@login_required
def provider_dashboard(request):
    if not request.user.is_provider():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()

    businesses = Business.objects.filter(owner=request.user, is_active=True)

    # Agregacije
    today = date.today()
    stats = {}
    for biz in businesses:
        stats[biz.id] = {
            'today_count': biz.appointments.filter(
                start_datetime__date=today,
                status=Appointment.STATUS_CONFIRMED
            ).count(),
            'pending_count': biz.appointments.filter(
                status=Appointment.STATUS_PENDING
            ).count(),
            'total_month': biz.appointments.filter(
                start_datetime__month=today.month,
                status=Appointment.STATUS_COMPLETED
            ).count(),
        }

    # Termini za danas
    today_appointments = Appointment.objects.filter(
        business__in=businesses,
        start_datetime__date=today
    ).select_related('client', 'service', 'staff').order_by('start_datetime')

    context = {
        'businesses': businesses,
        'stats': stats,
        'today_appointments': today_appointments,
        'today': today,
    }
    return render(request, 'provider/dashboard.html', context)
