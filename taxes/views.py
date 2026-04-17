from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Taxpayer, TaxType, TaxRecord
from .forms import TaxpayerForm, TaxRecordForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
import csv
from django.http import HttpResponse
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os


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
        'total_unpaid': total_unpaid,
        'tp_form': TaxpayerForm(),
        'tr_form': TaxRecordForm(),
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
        record.paid_at = timezone.now()
        record.save()
    except TaxRecord.DoesNotExist:
        pass  # Якщо запис не знайдено, просто ігноруємо

    return redirect('home')

# Додавання платника (Адмін)
@login_required
def taxpayer_add(request):
    if request.method == 'POST' and request.user.is_superuser:
        form = TaxpayerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Нового платника успішно додано до реєстру!')
            return redirect('home')
        else:
            messages.error(request, 'Помилка при додаванні. Перевірте введені дані.')
            # Якщо є помилки, заново збираємо дані для home і передаємо форму з помилками
            taxpayers = Taxpayer.objects.all()
            records = TaxRecord.objects.all()
            return render(request, 'index.html', {
                'taxpayers': taxpayers,
                'records': records,
                'tp_form': form,
                'tr_form': TaxRecordForm()
            })
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
        form = TaxRecordForm(request.POST)
        if form.is_valid():
            # Ми не зберігаємо відразу, бо треба розрахувати amount
            record = form.save(commit=False)
            income = form.cleaned_data['income']

            # Розрахунок податку: дохід * (ставка / 100)
            record.amount = income * (record.tax_type.rate / 100)
            record.save()
            return redirect('home')
    return redirect('home')

@login_required
def taxrecord_delete(request, pk):
    if request.user.is_superuser:
        TaxRecord.objects.filter(id=pk).delete()
    return redirect('home')


@login_required
def taxpayer_edit(request, pk):
    taxpayer = get_object_or_404(Taxpayer, pk=pk)
    if request.method == 'POST' and request.user.is_superuser:
        form = TaxpayerForm(request.POST, instance=taxpayer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Дані {taxpayer.full_name} оновлено!')
    return redirect('home')

@login_required
def taxrecord_edit(request, pk):
    record = get_object_or_404(TaxRecord, pk=pk)
    if request.method == 'POST' and request.user.is_superuser:
        form = TaxRecordForm(request.POST, instance=record)
        if form.is_valid():
            new_record = form.save(commit=False)
            # Перераховуємо суму податку на основі оновленого доходу
            income = form.cleaned_data['income']
            new_record.amount = income * (new_record.tax_type.rate / 100)
            new_record.save()
            messages.success(request, f"Запис для {record.taxpayer.full_name} оновлено.")
    return redirect('home')

@login_required
def export_taxpayers_csv(request):
    if not request.user.is_superuser:
        return redirect('home')

    # Створюємо HTTP-відповідь з правильним типом контенту
    response = HttpResponse(content_type='text/csv')
    # Додаємо заголовок файлу (українською мовою може бути проблема з кодуванням, тому використовуємо utf-8-sig)
    response['Content-Disposition'] = 'attachment; filename="taxpayers_report.csv"'
    response.write(u'\ufeff'.encode('utf8')) # Для коректного відображення кирилиці в Excel

    writer = csv.writer(response)
    writer.writerow(['ПІБ Платника', 'ІПН', 'Загальна сума нарахувань', 'Статус'])

    taxpayers = Taxpayer.objects.all()
    for tp in taxpayers:
        # Можеш додати логіку підрахунку суми прямо тут
        total = sum(record.amount for record in tp.taxrecord_set.all())
        writer.writerow([tp.full_name, tp.tin, f"{total:.2f}", "Активний"])

    return response


@login_required
def download_receipt(request, pk):
    record = get_object_or_404(TaxRecord, pk=pk)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # 1. Реєструємо український шрифт (Arial є на кожному Windows)
    font_path = "C:\\Windows\\Fonts\\arial.ttf"

    # Перевіримо, чи файл існує, щоб не "лягла" в'юха
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('ArialUA', font_path))
        p.setFont('ArialUA', 14)
    else:
        # Якщо раптом шляхи відрізняються, використаємо стандартний (але будуть крякозябри)
        p.setFont("Helvetica", 14)

    # 2. Малюємо текст (тепер він буде українською)
    p.drawString(100, 800, f"Квитанція про сплату податку №{record.id}")
    p.line(100, 790, 500, 790)

    p.setFont('ArialUA', 12) if os.path.exists(font_path) else p.setFont("Helvetica", 12)

    p.drawString(100, 760, f"Платник: {record.taxpayer.full_name}")
    p.drawString(100, 740, f"ІПН: {record.taxpayer.tin}")
    p.drawString(100, 720, f"Тип податку: {record.tax_type.name}")
    p.drawString(100, 700, f"Сума: {record.amount} грн")
    p.drawString(100, 680, f"Дата оплати: {record.paid_at.strftime('%d.%m.%Y %H:%M') if record.paid_at else '-'}")
    p.drawString(100, 660, f"Статус: ОПЛАЧЕНО")

    p.showPage()
    p.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf',
                        headers={'Content-Disposition': f'attachment; filename="receipt_{record.id}.pdf"'})