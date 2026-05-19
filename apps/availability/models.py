from django.db import models

DAYS_OF_WEEK = [
    (0, 'Ponedjeljak'),
    (1, 'Utorak'),
    (2, 'Srijeda'),
    (3, 'Četvrtak'),
    (4, 'Petak'),
    (5, 'Subota'),
    (6, 'Nedjelja'),
]


class WorkingHours(models.Model):
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE,
        related_name='working_hours'
    )
    staff = models.ForeignKey(
        'businesses.Staff', on_delete=models.CASCADE,
        null=True, blank=True, related_name='working_hours'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('business', 'staff', 'day_of_week')
        ordering = ['day_of_week']

    def __str__(self):
        day = dict(DAYS_OF_WEEK)[self.day_of_week]
        if self.is_closed:
            return f"{self.business} — {day}: Zatvoreno"
        return f"{self.business} — {day}: {self.open_time}–{self.close_time}"


class BlockedSlot(models.Model):
    """Blokirani termini (odmor, bolovanje, pauza)"""
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE, related_name='blocked_slots'
    )
    staff = models.ForeignKey(
        'businesses.Staff', on_delete=models.CASCADE,
        null=True, blank=True, related_name='blocked_slots'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Blokiran: {self.business} {self.start_datetime:%d.%m %H:%M}–{self.end_datetime:%H:%M}"
