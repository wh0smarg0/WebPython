from django.db import models
from django.contrib.auth.models import User

class TaxType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Назва податку")
    rate = models.FloatField(verbose_name="Ставка (%)")

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Taxpayer(models.Model):
    # Додаємо зв'язок Один-до-Одного з акаунтом для входу
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Обліковий запис")

    full_name = models.CharField(max_length=255, verbose_name="ПІБ платника")
    tin = models.CharField(max_length=10, unique=True, verbose_name="ІПН")

    def __str__(self):
        return self.full_name

class TaxRecord(models.Model):
    taxpayer = models.ForeignKey(Taxpayer, on_delete=models.CASCADE, verbose_name="Платник")
    tax_type = models.ForeignKey(TaxType, on_delete=models.CASCADE, verbose_name="Тип податку")
    amount = models.FloatField(verbose_name="Сума до сплати")
    is_paid = models.BooleanField(default=False, verbose_name="Статус оплати")

    def __str__(self):
        return f"{self.taxpayer.full_name} - {self.tax_type.name}: {self.amount}"
