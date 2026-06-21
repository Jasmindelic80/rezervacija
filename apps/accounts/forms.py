from django import forms
import re


def normalize_phone(phone: str, country_code: str = '+387') -> str:
    """
    Normalizuj broj telefona na međunarodni format.
    Za +387: 062 123 456 → +38762123456
    Za ostale: broj se kombinuje sa country_code prefiksom.
    """
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    if phone.startswith('+'):
        return phone
    if country_code == '+387':
        if phone.startswith('00387'):
            return '+387' + phone[5:]
        if phone.startswith('0') and not phone.startswith('00'):
            return '+387' + phone[1:]
        return '+387' + phone
    # International: strip leading 0 and prepend country code
    stripped = phone.lstrip('0')
    return country_code + stripped


# Common country codes for the region + EU
COUNTRY_CODES = [
    ('+387', '🇧🇦 BiH (+387)'),
    ('+385', '🇭🇷 Hrvatska (+385)'),
    ('+381', '🇷🇸 Srbija (+381)'),
    ('+382', '🇲🇪 Crna Gora (+382)'),
    ('+386', '🇸🇮 Slovenija (+386)'),
    ('+43',  '🇦🇹 Austrija (+43)'),
    ('+49',  '🇩🇪 Njemačka (+49)'),
    ('+41',  '🇨🇭 Švicarska (+41)'),
    ('+39',  '🇮🇹 Italija (+39)'),
    ('+33',  '🇫🇷 Francuska (+33)'),
    ('+44',  '🇬🇧 UK (+44)'),
    ('+31',  '🇳🇱 Holandija (+31)'),
    ('+46',  '🇸🇪 Švedska (+46)'),
    ('+47',  '🇳🇴 Norveška (+47)'),
    ('+45',  '🇩🇰 Danska (+45)'),
    ('+1',   '🇺🇸 SAD/Kanada (+1)'),
    ('+61',  '🇦🇺 Australija (+61)'),
]


class EmailPhoneForm(forms.Form):
    """Korak 1: Email (obavezno) + telefon (opciono)"""
    email = forms.EmailField(
        label='Email adresa',
        widget=forms.EmailInput(attrs={
            'placeholder': 'vas@email.com',
            'class': 'form-control form-control-lg',
            'autocomplete': 'email',
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label='Broj telefona',
        widget=forms.TextInput(attrs={
            'placeholder': '61 123 456',
            'class': 'form-control form-control-lg',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        })
    )
    country_code = forms.CharField(max_length=5, required=False, initial='+387')
    role = forms.ChoiceField(
        choices=[('client', 'Tražim usluge'), ('provider', 'Nudim usluge')],
        widget=forms.RadioSelect,
        initial='client',
    )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            return None
        country_code = self.data.get('country_code', '+387') or '+387'
        normalized = normalize_phone(phone, country_code)
        if not re.match(r'^\+[1-9]\d{6,14}$', normalized):
            raise forms.ValidationError('Unesite validan broj telefona.')
        return normalized


PhoneInputForm = EmailPhoneForm


class OTPVerifyForm(forms.Form):
    """Korak 2: Unos OTP koda"""
    otp = forms.CharField(
        max_length=6, min_length=6,
        label='Verifikacijski kod',
        widget=forms.TextInput(attrs={
            'placeholder': '------',
            'class': 'form-control form-control-lg text-center otp-input',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'maxlength': '6',
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data['otp']
        if not otp.isdigit():
            raise forms.ValidationError('Kod može sadržavati samo cifre.')
        return otp


class CompleteProfileForm(forms.Form):
    """Korak 3: Dopuna profila (ime, lozinka)"""
    first_name = forms.CharField(
        max_length=50, label='Ime',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vaše ime'})
    )
    last_name = forms.CharField(
        max_length=50, label='Prezime',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vaše prezime'})
    )
    password = forms.CharField(
        label='Lozinka',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min. 8 karaktera'})
    )
    password_confirm = forms.CharField(
        label='Potvrda lozinke',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ponovite lozinku'})
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError({'password_confirm': 'Lozinke se ne podudaraju.'})
        if p1 and len(p1) < 8:
            raise forms.ValidationError({'password': 'Lozinka mora imati najmanje 8 karaktera.'})
        return cleaned

