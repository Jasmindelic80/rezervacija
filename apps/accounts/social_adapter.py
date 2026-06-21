from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """Poveži social login s postojećim userom ako email već postoji."""
        if sociallogin.is_existing:
            return
        extra = sociallogin.account.extra_data
        email = extra.get('email', '')
        if not email:
            return
        # Odbij ako je email eksplicitno nepotvrđen (Google šalje email_verified)
        if extra.get('email_verified') is False:
            return
        try:
            existing = User.objects.get(email=email)
            sociallogin.connect(request, existing)
        except User.DoesNotExist:
            pass

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        # Postavi role na client po defaultu
        user.role = 'client'
        # Generiraj username ako ga nema
        if not user.username:
            email = data.get('email', '')
            base = email.split('@')[0] if email else 'user'
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{counter}'
                counter += 1
            user.username = username
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        user = socialaccount.user
        if user.is_provider():
            return '/termin/dashboard/'
        return '/'
