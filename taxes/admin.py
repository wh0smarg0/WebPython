from django.contrib import admin
from .models import Taxpayer, TaxType, TaxRecord

admin.site.register(Taxpayer)
admin.site.register(TaxType)
admin.site.register(TaxRecord)