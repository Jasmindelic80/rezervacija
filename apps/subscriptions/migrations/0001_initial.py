from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('businesses', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('trial', 'Probni period'),
                        ('active', 'Aktivan'),
                        ('expired', 'Istekao'),
                        ('cancelled', 'Otkazan'),
                    ],
                    default='trial', max_length=20
                )),
                ('trial_end', models.DateTimeField()),
                ('active_until', models.DateTimeField(blank=True, null=True)),
                ('monthly_price', models.DecimalField(decimal_places=2, default=Decimal('19.99'), max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscription',
                    to='businesses.business',
                )),
            ],
            options={'verbose_name': 'Pretplata', 'verbose_name_plural': 'Pretplate'},
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(
                    choices=[('paypal', 'PayPal'), ('bank', 'Bankovna uplata')],
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Na čekanju'),
                        ('confirmed', 'Potvrđeno'),
                        ('rejected', 'Odbijeno'),
                    ],
                    default='pending', max_length=20,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('months', models.PositiveIntegerField(default=1)),
                ('reference', models.CharField(blank=True, max_length=300)),
                ('proof', models.FileField(
                    blank=True, null=True,
                    upload_to='payment_proofs/',
                    verbose_name='Dokaz uplate',
                )),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('subscription', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to='subscriptions.subscription',
                )),
            ],
            options={'verbose_name': 'Uplata', 'verbose_name_plural': 'Uplate', 'ordering': ['-created_at']},
        ),
    ]
