"""PayPal Orders API v2 — koristi httpx koji je već u requirements."""
import httpx
from django.conf import settings


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
    resp = httpx.post(
        f'{base}/v2/checkout/orders',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={
            'intent': 'CAPTURE',
            'purchase_units': [{
                'amount': {'currency_code': 'BAM', 'value': str(amount_bam)},
                'description': 'RezervišiBiH — pretplata',
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': 'RezervišiBiH',
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
