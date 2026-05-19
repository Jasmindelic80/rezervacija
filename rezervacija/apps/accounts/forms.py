from django import forms
import re


def normalize_phone(phone: str) -> str:
    """
    Normalizuj bosanski broj telefona na međunarodni format.
    062 123 456  →  +38762123456
    +387 62 123 456  →  +38762123456
    """
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    if phone.startswith('00387'):
        phone = '+387' + phone[5:]
    elif phone.startswith('0') and not phone.startswith('00'):
        phone = '+387' + phone[1:]
    elif not phone.startswith('+'):
        phone = '+387' + phone
    return phone


class PhoneInputForm(forms.Form):
    """Korak 1: Unos broja telefona"""
    phone = forms.CharField(
        max_length=20,
        label='Broj telefona',
        widget=forms.TextInput(attrs={
            'placeholder': '061 123 456',
            'class': 'form-control form-control-lg',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        })
    )
    role = forms.ChoiceField(
        choices=[('client', 'Tražim usluge'), ('provider', 'Nudim usluge')],
        widget=forms.RadioSelect,
        initial='client',
    )

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        normalized = normalize_phone(phone)
        # Provjeri format +387XXXXXXXX
        if not re.match(r'^\+387[6][0-9]{7,8}$', normalized):
            raise forms.ValidationError(
                'Unesite validan BiH broj telefona (npr. 061 123 456)'
            )
        return normalized


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
    email = forms.EmailField(
        required=False, label='Email (opciono)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@primjer.ba'})
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

