from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=100, blank=True)  # CSS klasa ili emoji
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Business(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='businesses'
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name='businesses'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    canton = models.CharField(max_length=100, blank=True)
    entity = models.CharField(
        max_length=20,
        choices=[('fbih', 'FBiH'), ('rs', 'RS'), ('bd', 'Brčko Distrikt')],
        default='fbih'
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    facebook = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    cover_image = models.ImageField(
        upload_to='business_covers/', blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    accepts_walk_in = models.BooleanField(default=False)
    appointment_interval_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Interval između termina u minutama"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Businesses'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Business.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return reviews.aggregate(avg=models.Avg('rating'))['avg']
        return None

    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    def has_available_slots_today(self):
        """Brza provjera ima li slobodnih termina danas"""
        from apps.appointments.models import Appointment
        from datetime import date
        today = date.today()
        return not Appointment.objects.filter(
            business=self,
            start_datetime__date=today,
            status__in=['pending', 'confirmed']
        ).count() >= 10  # Simplified check


class Staff(models.Model):
    """Radnici / majstori u biznisu"""
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='staff'
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staff_profiles'
    )
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True)  # "Senior frizer"
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} @ {self.business.name}"


class BusinessPhoto(models.Model):
    """Galerija slika biznisa"""
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='photos'
    )
    image = models.ImageField(upload_to='business_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']


class Review(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='reviews'
    )
    appointment = models.OneToOneField(
        'appointments.Appointment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='review'
    )
    client = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews'
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('business', 'client')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client} → {self.business} ({self.rating}⭐)"
