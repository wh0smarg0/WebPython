from django import forms
from .models import Taxpayer, TaxRecord, TaxType
import re

class TaxpayerForm(forms.ModelForm):
    class Meta:
        model = Taxpayer
        fields = ['full_name', 'tin']
        labels = {
            'full_name': 'ПІБ платника',
            'tin': 'ІПН (10 цифр)',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Прізвище, Ім’я, По батькові'}),
            'tin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0123456789'}),
        }

    # Валідація ІПН
    def clean_tin(self):
        tin = self.cleaned_data.get('tin')

        # 1. Базова валідація формату
        if not tin.isdigit():
            raise forms.ValidationError("ІПН повинен містити лише цифри.")
        if len(tin) != 10:
            raise forms.ValidationError("ІПН повинен складатися рівно з 10 цифр.")

        # 2. Перевірка на унікальність (тільки для нових записів)
        # self.instance.pk перевіряє, чи ми редагуємо існуючого платника чи створюємо нового
        if not self.instance.pk:
            if Taxpayer.objects.filter(tin=tin).exists():
                raise forms.ValidationError("Платник з таким ІПН вже зареєстрований у системі.")

        return tin

class TaxRecordForm(forms.ModelForm):
    # Додаємо поле для введення доходу (якого немає в моделі)
    income = forms.FloatField(
        label="Сума доходу (грн)",
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    class Meta:
        model = TaxRecord
        fields = ['taxpayer', 'tax_type']
        widgets = {
            'taxpayer': forms.Select(attrs={'class': 'form-select'}),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
        }

    # Валідація доходу
    def clean_income(self):
        income = self.cleaned_data.get('income')
        if income <= 0:
            raise forms.ValidationError("Дохід має бути більшим за нуль.")
        return income