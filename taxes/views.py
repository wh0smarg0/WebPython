from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Taxpayer, TaxType, TaxRecord


@login_required(login_url='/login/')
def home(request):
    if request.user.is_superuser:
        # АДМІН: Бачить усе
        taxpayers = Taxpayer.objects.all().order_by('id')
        tax_types = TaxType.objects.all().order_by('id')
        records = TaxRecord.objects.select_related('taxpayer', 'tax_type').all().order_by('-id')
        total_unpaid = 0
    else:
        # КОРИСТУВАЧ:
        tax_types = TaxType.objects.all()

        if hasattr(request.user, 'taxpayer'):
            current_tp = request.user.taxpayer
            taxpayers = [current_tp]
            # Беремо записи саме цього користувача
            records = TaxRecord.objects.filter(taxpayer=current_tp).select_related('taxpayer', 'tax_type').order_by(
                '-id')

            # ПУНКТ 1: Рахуємо суму тільки неоплачених податків
            total_unpaid = records.filter(is_paid=False).aggregate(Sum('amount'))['amount__sum'] or 0
        else:
            taxpayers = []
            records = []
            total_unpaid = 0

    context = {
        'taxpayers': taxpayers,
        'tax_types': tax_types,
        'records': records,
        'total_unpaid': total_unpaid,  # Тепер ця змінна піде в шаблон
    }
    return render(request, 'index.html', context)


@login_required(login_url='/login/')
def declare_tax(request):
    if request.method == 'POST':
        tax_type_id = request.POST.get('tax_type_id')
        income_str = request.POST.get('income')

        if income_str and hasattr(request.user, 'taxpayer'):
            income = float(income_str)
            tax_type = TaxType.objects.get(id=tax_type_id)

            TaxRecord.objects.create(
                taxpayer=request.user.taxpayer,
                tax_type=tax_type,
                amount=income * (tax_type.rate / 100)
            )
    return redirect('home')


@login_required(login_url='/login/')
def pay_tax(request, record_id):
    # ПУНКТ 3: Знаходимо запис і міняємо статус на "Оплачено"
    try:
        record = TaxRecord.objects.get(id=record_id, taxpayer=request.user.taxpayer)
        record.is_paid = True
        record.save()
    except TaxRecord.DoesNotExist:
        pass  # Якщо запис не знайдено, просто ігноруємо

    return redirect('home')

# Додавання платника (Адмін)
@login_required
def taxpayer_add(request):
    if request.method == 'POST' and request.user.is_superuser:
        Taxpayer.objects.create(
            full_name=request.POST.get('full_name'),
            tin=request.POST.get('tin')
        )
    return redirect('home')

# Видалення платника (Адмін)
@login_required
def taxpayer_delete(request, pk):
    if request.user.is_superuser:
        Taxpayer.objects.filter(id=pk).delete()
    return redirect('home')

# Додавання нового типу податку (Адмін)
@login_required
def taxtype_add(request):
    if request.method == 'POST' and request.user.is_superuser:
        TaxType.objects.create(
            name=request.POST.get('name'),
            rate=float(request.POST.get('rate'))
        )
    return redirect('home')

# Створення нарахування Адміном
@login_required
def taxrecord_add(request):
    if request.method == 'POST' and request.user.is_superuser:
        tp = Taxpayer.objects.get(id=request.POST.get('taxpayer_id'))
        tt = TaxType.objects.get(id=request.POST.get('tax_type_id'))
        income = float(request.POST.get('income'))
        TaxRecord.objects.create(
            taxpayer=tp,
            tax_type=tt,
            amount=income * (tt.rate / 100)
        )
    return redirect('home')

@login_required
def taxrecord_delete(request, pk):
    if request.user.is_superuser:
        TaxRecord.objects.filter(id=pk).delete()
    return redirect('home')