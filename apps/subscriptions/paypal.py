"""PayPal Orders API v2 — koristi httpx koji je već u requirements."""
from decimal import Decimal, ROUND_HALF_UP

import httpx
from django.conf import settings

# BAM je fiksno vezan za EUR (currency board) — kurs je zakonski fiksan i ne mijenja se.
BAM_PER_EUR = Decimal('1.95583')


def convert_amount(amount_bam) -> Decimal:
    """Cijene u bazi su u BAM; PayPal ne podržava BAM pa se za EUR nalog preračunava po fiksnom kursu."""
    amount_bam = Decimal(str(amount_bam))
    if settings.PAYPAL_CURRENCY == 'EUR':
        return (amount_bam / BAM_PER_EUR).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return amount_bam.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _get_access_token():
    mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
    base = 'https://api-m.sandbox.paypal.com' if mode == 'sandbox' else 'https://api-m.paypal.com'
    resp = httpx.post(
        f'{base}/v1/oauth2/token',
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={'grant_type': 'client_credentials'},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()['access_token'], base


def create_order(amount_bam: str, return_url: str, cancel_url: str) -> dict:
    token, base = _get_access_token()
    charge_amount = convert_amount(amount_bam)
    resp = httpx.post(
        f'{base}/v2/checkout/orders',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {'currency_code': settings.PAYPAL_CURRENCY, 'value': str(charge_amount)},
                'description': 'BookBiH — pretplata',
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': 'BookBiH',
                'landing_page': 'BILLING',
                'user_action': 'PAY_NOW',
            },
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    approve_url = next(
        (l['href'] for l in data.get('links', []) if l['rel'] == 'approve'), None
    )
    return {'order_id': data['id'], 'approve_url': approve_url}


def capture_order(order_id: str) -> dict:
    token, base = _get_access_token()
    resp = httpx.post(
        f'{base}/v2/checkout/orders/{order_id}/capture',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
