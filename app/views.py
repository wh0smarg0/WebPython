from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from datetime import datetime
import csv
from io import StringIO

# Імпорти для аутентифікації [cite: 715]
from flask_login import login_user, current_user, logout_user, login_required

# Імпорти з нашого пакета (використовуємо відносні імпорти) [cite: 713-716]
from . import db
from .models import User, Taxpayer, TaxRecord, TaxType
from .forms import TaxpayerForm, TaxRecordForm, LoginForm

from xhtml2pdf import pisa
from io import BytesIO

import base64
import os
from flask import current_app

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Створюємо Blueprint замість використання app безпосередньо
main = Blueprint('main', __name__)

# --- АВТОРИЗАЦІЯ ---

@main.route('/login/', methods=['GET', 'POST'])
def login():
    # Якщо користувач вже авторизований, не показуємо форму [cite: 618, 727]
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        # Пошук користувача за логіном [cite: 731-732]
        user = User.query.filter_by(username=form.username.data).first()

        # Перевірка пароля через хеш [cite: 733]
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data) # Вхід [cite: 734]
            flash("Успішний вхід у систему!", "success")
            return redirect(url_for('main.index'))

        flash("Невірний логін або пароль", "error")

    return render_template('login.html', form=form)

@main.route('/logout/')
@login_required # Доступ тільки для авторизованих [cite: 739]
def logout():
    logout_user() # Завершення сесії [cite: 741]
    flash("Ви вийшли з акаунта.", "info")
    return redirect(url_for('main.login'))

# --- ГОЛОВНА СТОРІНКА (Адмін-панель) ---

@main.route('/')
@login_required
def index():
    # 1. Визначаємо список платників залежно від ролі
    if current_user.username == 'admin':
        taxpayers = Taxpayer.query.all()
    else:
        # Тільки ті, що належать поточному юзеру
        taxpayers = Taxpayer.query.filter_by(user_id=current_user.id).all()

    # 2. Отримуємо ID платників, щоб відфільтрувати їхні нарахування
    tp_ids = [t.id for t in taxpayers]
    records = TaxRecord.query.filter(TaxRecord.taxpayer_id.in_(tp_ids)).all() if tp_ids else []

    tax_types = TaxType.query.all()
    tp_form = TaxpayerForm()
    tr_form = TaxRecordForm()

    # Розрахунок загального боргу для користувача
    total_unpaid = sum(r.amount for r in records if not r.is_paid)

    return render_template('index.html',
                           taxpayers=taxpayers,
                           records=records,
                           tax_types=tax_types,
                           tp_form=tp_form,
                           tr_form=tr_form,
                           total_unpaid=total_unpaid)

# --- УПРАВЛІННЯ ПЛАТНИКАМИ (CRUD) ---

@main.route('/taxpayer/add', methods=['POST'])
@login_required
def taxpayer_add():
    form = TaxpayerForm()
    if form.validate_on_submit():
        new_tp = Taxpayer(full_name=form.full_name.data, tin=form.tin.data)
        db.session.add(new_tp)
        db.session.commit()
        flash('Платника успішно додано!', 'success')
    return redirect(url_for('main.index'))


@main.route('/taxpayer/edit/<int:pk>', methods=['POST'])
@login_required
def taxpayer_edit(pk):
    tp = Taxpayer.query.get_or_404(pk)

    # Отримуємо дані з форми
    name = request.form.get('full_name')
    tin = request.form.get('tin')

    try:
        if name:
            tp.full_name = name
        if tin:
            # Перевіряємо довжину перед записом
            if len(tin) == 10:
                tp.tin = tin
            else:
                flash("Помилка: ІПН не може бути довшим за 10 символів!", "danger")
                return redirect(url_for('main.index'))

        db.session.commit()
        flash('Дані платника успішно оновлено!', 'success')
    except Exception as e:
        db.session.rollback()
        # Якщо ІПН вже існує, виникне IntegrityError
        flash(f"Помилка при оновленні: можливо, такий ІПН уже існує.", "danger")
        print(f"Database error: {e}")  # Дивись помилку в терміналі PyCharm

    return redirect(url_for('main.index'))

@main.route('/taxpayer/delete/<int:pk>')
@login_required
def taxpayer_delete(pk):
    tp = Taxpayer.query.get_or_404(pk)
    db.session.delete(tp)
    db.session.commit()
    flash('Платника видалено.', 'warning')
    return redirect(url_for('main.index'))

# --- ЖУРНАЛ НАРАХУВАНЬ ---

@main.route('/record/add', methods=['POST'])
@login_required
def taxrecord_add():
    tp_id = request.form.get('taxpayer_id')
    tt_id = request.form.get('tax_type_id')
    income_val = float(request.form.get('income'))

    tax_type = TaxType.query.get(tt_id)
    # Розрахунок суми податку
    tax_amount = income_val * (tax_type.rate / 100)

    new_record = TaxRecord(taxpayer_id=tp_id, tax_type_id=tt_id, amount=tax_amount)
    db.session.add(new_record)
    db.session.commit()
    flash('Нарахування додано!', 'success')
    return redirect(url_for('main.index'))

@main.route('/record/edit/<int:pk>', methods=['POST'])
@login_required
def record_edit(pk):
    record = TaxRecord.query.get_or_404(pk)
    tp_id = request.form.get('taxpayer')
    tt_id = request.form.get('tax_type')
    income_val = request.form.get('income')

    if income_val:
        tax_type = TaxType.query.get(tt_id)
        record.taxpayer_id = tp_id
        record.tax_type_id = tt_id
        record.amount = float(income_val) * (tax_type.rate / 100)
        db.session.commit()
        flash('Запис оновлено та суму перераховано!', 'success')
    return redirect(url_for('main.index'))

@main.route('/record/delete/<int:pk>')
@login_required
def taxrecord_delete(pk):
    record = TaxRecord.query.get_or_404(pk)
    db.session.delete(record)
    db.session.commit()
    flash('Запис видалено.', 'info')
    return redirect(url_for('main.index'))

# --- СЕРВІСНІ ФУНКЦІЇ ---

@main.route('/pay/<int:record_id>')
@login_required
def pay_tax(record_id):
    record = TaxRecord.query.get_or_404(record_id)
    record.is_paid = True
    record.paid_at = datetime.utcnow()
    db.session.commit()
    flash(f'Суму {record.amount} грн сплачено!', 'success')
    return redirect(url_for('main.index'))

@main.route('/export-csv')
@login_required
def export_taxpayers_csv():
    si = StringIO()
    si.write('\ufeff') # BOM для Excel
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['ID', 'Платник', 'ІПН', 'Сума', 'Статус'])

    records = TaxRecord.query.all()
    for r in records:
        cw.writerow([r.id, r.taxpayer.full_name, r.taxpayer.tin, f"{r.amount:.2f}", 'Сплачено' if r.is_paid else 'Борг'])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=tax_report.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output


@main.route('/receipt/<int:pk>')
@login_required
def download_receipt(pk):
    record = TaxRecord.query.get_or_404(pk)

    if not record.is_paid:
        flash("Спочатку оплатіть податок!", "danger")
        return redirect(url_for('main.index'))

    # 1. Реєструємо шрифт у системі ReportLab (це завантажить його в пам'ять)
    font_path = os.path.join(current_app.root_path, 'static', 'fonts', 'times.ttf')
    try:
        # Реєструємо шрифт під назвою 'Arial'
        pdfmetrics.registerFont(TTFont('Times', font_path))
    except Exception as e:
        return f"Помилка завантаження шрифту: {e}", 500

    # 2. Рендеримо шаблон БЕЗ передачі font_base64 (він нам більше не потрібен!)
    html = render_template('receipt_pdf.html', record=record)

    result = BytesIO()
    # 3. Створюємо PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=receipt_{record.id}.pdf'
        return response

    return "Помилка при генерації PDF", 500


# --- ПОДАТИ ДЕКЛАРАЦІЮ (User Side) ---
@main.route('/declare', methods=['POST'])
@login_required
def declare_tax():
    # Шукаємо профіль платника, який належить ЦЬОМУ користувачу
    current_tp = Taxpayer.query.filter_by(user_id=current_user.id).first()

    if not current_tp:
        flash("У вас ще немає профілю платника. Зверніться до адміністратора.", "danger")
        return redirect(url_for('main.index'))

    tt_id = request.form.get('tax_type_id')
    income_val = request.form.get('income')
    tax_type = TaxType.query.get(tt_id)

    amount = float(income_val) * (tax_type.rate / 100)
    new_record = TaxRecord(taxpayer_id=current_tp.id, tax_type_id=tt_id, amount=amount)

    db.session.add(new_record)
    db.session.commit()

    flash('Декларацію подано успішно!', 'success')
    return redirect(url_for('main.index'))


# --- ДОДАВАННЯ ТИПУ ПОДАТКУ (Admin) ---
@main.route('/taxtype/add', methods=['POST'])
@login_required
def taxtype_add():
    name = request.form.get('name')
    rate = request.form.get('rate')

    if name and rate:
        new_type = TaxType(name=name, rate=float(rate))
        db.session.add(new_type)
        db.session.commit()
        flash('Нову ставку податку збережено!', 'success')
    else:
        flash('Помилка: заповніть усі поля для нової ставки', 'danger')

    return redirect(url_for('main.index'))