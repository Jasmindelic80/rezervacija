from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Subscription, Payment, plan_amount


def _get_subscription(request, slug=None):
    qs = request.user.businesses.select_related('subscription')
    business = qs.filter(slug=slug).first() if slug else qs.first()
    if not business:
        return None, None
    try:
        return business, business.subscription
    except Subscription.DoesNotExist:
        return business, None


@login_required
def subscription_dashboard(request, slug=None):
    business, sub = _get_subscription(request, slug)
    if not business:
        messages.info(request, 'Prvo registrujte vaš biznis.')
        return redirect('register_business')
    if not sub:
        messages.error(request, 'Pretplata nije pronađena. Kontaktirajte podršku.')
        return redirect('home')

    sub.sync_status()
    payments = sub.payments.order_by('-created_at')
    return render(request, 'subscriptions/dashboard.html', {
        'sub': sub,
        'business': business,
        'payments': payments,
    })


@login_required
def payment_choose(request, slug=None):
    business, sub = _get_subscription(request, slug)
    if not sub:
        return redirect('home')

    months = int(request.GET.get('months', 1))
    months = max(1, min(months, 12))
    amount = plan_amount(sub.monthly_price, months)

    annual_full_price = sub.monthly_price * 12
    annual_total = plan_amount(sub.monthly_price, 12)
    annual_savings_pct = round((1 - annual_total / annual_full_price) * 100) if annual_full_price else 0

    month_options = [
        (1, '1 mjesec', ''),
        (3, '3 mjeseca', ''),
        (6, '6 mjeseci', 'Popularno'),
        (12, '12 mjeseci', f'Uštedi {annual_savings_pct}%'),
    ]

    return render(request, 'subscriptions/payment_choose.html', {
        'sub': sub,
        'business': business,
        'months': months,
        'amount': amount,
        'monthly_price': sub.monthly_price,
        'month_options': [(m, lbl, note, plan_amount(sub.monthly_price, m)) for m, lbl, note in month_options],
    })


@login_required
@require_POST
def payment_bank_initiate(request, slug=None):
    business, sub = _get_subscription(request, slug)
    if not sub:
        return redirect('home')

    months = int(request.POST.get('months', 1))
    months = max(1, min(months, 12))
    amount = plan_amount(sub.monthly_price, months)

    payment = Payment.objects.create(
        subscription=sub,
        method=Payment.METHOD_BANK,
        amount=amount,
        months=months,
        status=Payment.STATUS_PENDING,
    )

    return render(request, 'subscriptions/payment_bank.html', {
        'sub': sub,
        'business': business,
        'payment': payment,
        'bank_name': getattr(settings, 'BANK_NAME', 'Raiffeisen Bank d.d. BiH'),
        'bank_iban': getattr(settings, 'BANK_IBAN', 'BA391610000000123456'),
        'bank_swift': getattr(settings, 'BANK_SWIFT', 'RZBABA2S'),
        'bank_account_owner': getattr(settings, 'BANK_ACCOUNT_OWNER', 'BookBiH d.o.o.'),
    })


_ALLOWED_PROOF_CONTENT_TYPES = {'image/jpeg', 'image/png', 'application/pdf'}
_ALLOWED_PROOF_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
_MAX_PROOF_SIZE = 5 * 1024 * 1024  # 5 MB


@login_required
def payment_bank_upload(request, payment_id):
    """Upload dokaza uplate."""
    import os
    payment = get_object_or_404(
        Payment, id=payment_id, subscription__business__owner=request.user
    )
    business, sub = payment.subscription.business, payment.subscription

    if request.method == 'POST' and request.FILES.get('proof'):
        f = request.FILES['proof']
        ext = os.path.splitext(f.name)[1].lower()
        if f.content_type not in _ALLOWED_PROOF_CONTENT_TYPES or ext not in _ALLOWED_PROOF_EXTENSIONS:
            messages.error(request, 'Dozvoljeni formati: JPG, PNG, PDF.')
        elif f.size > _MAX_PROOF_SIZE:
            messages.error(request, 'Maksimalna veličina fajla je 5 MB.')
        else:
            payment.proof = f
            payment.notes = request.POST.get('notes', '')
            payment.save(update_fields=['proof', 'notes'])
            messages.success(
                request,
                'Dokaz uplate je poslan. Aktivirat ćemo vašu pretplatu u roku od 24h.'
            )
            return redirect('subscription_dashboard')

    return render(request, 'subscriptions/payment_bank_upload.html', {
        'payment': payment,
        'business': business,
    })


@login_required
@require_POST
def payment_paypal_create(request, slug=None):
    business, sub = _get_subscription(request, slug)
    if not sub:
        return redirect('home')

    months = int(request.POST.get('months', 1))
    months = max(1, min(months, 12))
    amount = plan_amount(sub.monthly_price, months)

    payment = Payment.objects.create(
        subscription=sub,
        method=Payment.METHOD_PAYPAL,
        amount=amount,
        months=months,
        status=Payment.STATUS_PENDING,
    )

    return_url = request.build_absolute_uri(
        reverse('payment_paypal_capture', args=[payment.id])
    )
    cancel_url = request.build_absolute_uri(reverse('subscription_dashboard'))

    try:
        from .paypal import create_order
        result = create_order(str(amount), return_url, cancel_url)
        payment.reference = result['order_id']
        payment.save(update_fields=['reference'])
        return redirect(result['approve_url'])
    except Exception as e:
        payment.delete()
        messages.error(request, f'PayPal greška: {e}. Pokušajte bankovnu uplatu.')
        return redirect('payment_choose')


@login_required
def payment_paypal_capture(request, payment_id):
    payment = get_object_or_404(
        Payment, id=payment_id, subscription__business__owner=request.user
    )
    business, sub = payment.subscription.business, payment.subscription

    token = request.GET.get('token')  # PayPal šalje order ID kao token
    if not token or payment.status == Payment.STATUS_CONFIRMED:
        return redirect('subscription_dashboard')

    # Provjeri da token odgovara order-u koji smo kreirali
    if token != payment.reference:
        messages.error(request, 'Nevažeći PayPal token. Kontaktirajte podršku.')
        return redirect('subscription_dashboard')

    try:
        from .paypal import capture_order
        result = capture_order(token)
        status = result.get('status')
        if status == 'COMPLETED':
            # Provjeri da je naplaćeni iznos ispravan (cijena je u BAM, PayPal naplaćuje u PAYPAL_CURRENCY)
            try:
                from .paypal import convert_amount
                captures = result['purchase_units'][0]['payments']['captures']
                captured_value = Decimal(captures[0]['amount']['value'])
                expected_value = convert_amount(payment.amount)
                if captured_value < expected_value:
                    messages.error(request, 'PayPal iznos ne odgovara. Kontaktirajte podršku.')
                    return redirect('subscription_dashboard')
            except (KeyError, IndexError, Exception):
                pass

            payment.status = Payment.STATUS_CONFIRMED
            payment.confirmed_at = timezone.now()
            payment.save(update_fields=['status', 'confirmed_at'])
            sub.extend(months=payment.months)
            messages.success(
                request,
                f'PayPal uplata potvrđena! Pretplata aktivna {payment.months} mj.'
            )
        else:
            messages.warning(request, f'PayPal status: {status}. Kontaktirajte podršku.')
    except Exception as e:
        messages.error(request, f'Greška pri PayPal potvrdi: {e}')

    return redirect('subscription_dashboard')


def subscription_expired(request):
    business = sub = None
    if request.user.is_authenticated:
        business, sub = _get_subscription(request)
        if sub:
            sub.sync_status()

    return render(request, 'subscriptions/expired.html', {
        'sub': sub,
        'business': business,
    })
