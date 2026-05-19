from django.db import models


class ServiceCategory(models.Model):
    """Pod-kategorije usluga unutar biznisa (npr. 'Šišanje', 'Bojanje')"""
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE,
        related_name='service_categories'
    )
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.business.name})"


class Service(models.Model):
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE, related_name='services'
    )
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='services'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        help_text="Trajanje usluge u minutama"
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)
    price_note = models.CharField(
        max_length=100, blank=True,
        help_text="npr. 'od 20 KM' ili 'po dogovoru'"
    )
    is_active = models.BooleanField(default=True)
    requires_consultation = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min) — {self.price} KM"

    def price_display(self):
        if self.price_note:
            return self.price_note
        return f"{self.price} KM"


class StaffService(models.Model):
    """Koje usluge nudi koji radnik"""
    staff = models.ForeignKey(
        'businesses.Staff', on_delete=models.CASCADE, related_name='staff_services'
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='staff_services'
    )

    class Meta:
        unique_together = ('staff', 'service')
