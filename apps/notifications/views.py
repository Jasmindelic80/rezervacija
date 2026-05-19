from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import NotificationPreference


@login_required
def notification_settings(request):
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        prefs.preferred_channel = request.POST.get('preferred_channel', 'viber')
        prefs.receive_confirmation = 'receive_confirmation' in request.POST
        prefs.receive_reminder_24h = 'receive_reminder_24h' in request.POST
        prefs.receive_reminder_2h = 'receive_reminder_2h' in request.POST
        prefs.receive_cancellation = 'receive_cancellation' in request.POST
        prefs.save()
        messages.success(request, 'Postavke notifikacija su sačuvane.')
        return redirect('notification_settings')

    return render(request, 'accounts/notification_settings.html', {'prefs': prefs})