from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_mail import Message
from datetime import datetime
import csv
from io import StringIO
import random

# Імпорти для аутентифікації
from flask_login import login_user, current_user, logout_user, login_required

# Імпорти з пакета
from . import db
from .models import User, Taxpayer, TaxRecord, TaxType, AuditLog
from .forms import TaxpayerForm, TaxRecordForm, LoginForm
from . import mail
from .forms import RegistrationForm

from xhtml2pdf import pisa
from io import BytesIO

import base64
import os
from flask import current_app

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Створюємо Blueprint замість використання app безпосередньо
main = Blueprint('main', __name__)

def log_action(action, details=None, user_id=None):
    # Якщо user_id не передано, беремо поточного юзера (для оплати тощо)
    # Якщо ми в реєстрації — передамо ID вручну
    target_id = user_id if user_id else current_user.id
    log = AuditLog(user_id=target_id, action=action, details=details)
    db.session.add(log)

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
    # Визначаємо дані залежно від ролі (Адмін бачить все, Юзер - своє)
    if current_user.is_admin:
        taxpayers = Taxpayer.query.all()
        records = TaxRecord.query.all()
    else:
        taxpayers = Taxpayer.query.filter_by(user_id=current_user.id).all()
        tp_ids = [t.id for t in taxpayers]
        records = TaxRecord.query.filter(TaxRecord.taxpayer_id.in_(tp_ids)).all() if tp_ids else []

    # Отримуємо типи податків для виводу та форми
    tax_types = TaxType.query.all()

    # Ініціалізуємо форми
    tp_form = TaxpayerForm()
    tr_form = TaxRecordForm()

    # Заповнюємо випадаючі списки (choices)
    tr_form.taxpayer_id.choices = [(t.id, t.full_name) for t in taxpayers]

    # Список типів податків: назва + ставка для зручності
    tr_form.tax_type_id.choices = [(t.id, f"{t.name} ({t.rate}%)") for t in tax_types]

    # Розрахунок загального боргу
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

    log_action("Новий платник", f"Додано: {form.full_name.data}")
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

    log_action("Створення нарахування", f"Сума: {tax_amount:.2f} грн для ID платника {tp_id}")

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

    # --- НАДСИЛАННЯ ЛИСТА ---
    try:
        msg = Message(f"Підтвердження оплати податку №{record.id}",
                      recipients=[current_user.email])
        msg.body = f"Шановний(а) {current_user.name}!\n\n" \
                   f"Ваш платіж за '{record.tax_type.name}' на суму {record.amount:.2f} грн успішно прийнято.\n" \
                   f"Ви можете завантажити квитанцію в особистому кабінеті."
        mail.send(msg)
        flash(f'Суму {record.amount} грн сплачено, підтвердження надіслано на {current_user.email}!', 'success')
    except Exception as e:
        flash(f'Платіж прийнято, але не вдалося надіслати лист: {str(e)}', 'warning')

    log_action("Оплата податку", f"Запис #{record_id} успішно сплачено.")
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


@main.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash("У вас немає прав доступу!", "danger")
        return redirect(url_for('main.index'))

    users = User.query.all()
    # Витягуємо логи
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()

    # ВАЖЛИВО: додай logs=logs у рендер!
    return render_template('admin_users.html', users=users, logs=logs)


@main.route('/admin/user/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash("Головного адміністратора не можна видалити!", "danger")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"Користувача {user.username} видалено.", "success")
    return redirect(url_for('admin_users'))


@main.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # 1. Створюємо об'єкт користувача
        user = User(
            name=form.name.data,
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)

        # Перевірка на права адміністратора
        if user.username.lower() == 'admin':
            user.is_admin = True

        db.session.add(user)
        db.session.flush()  # Отримуємо ID користувача для зв'язку

        log_action("Реєстрація", f"Новий користувач: {user.username}", user_id=user.id)

        db.session.commit()

        # 2. Логіка тільки для звичайних користувачів (НЕ адмінів)
        if not user.is_admin:
            # Генеруємо ІПН
            auto_tin = ''.join([str(random.randint(0, 9)) for _ in range(10)])

            # Перевірка на унікальність ІПН
            while Taxpayer.query.filter_by(tin=auto_tin).first():
                auto_tin = ''.join([str(random.randint(0, 9)) for _ in range(10)])

            # Створюємо профіль платника
            new_taxpayer = Taxpayer(
                full_name=user.name,
                tin=auto_tin,
                user_id=user.id
            )
            db.session.add(new_taxpayer)
            flash(f'Акаунт створено! Ваш автоматичний ІПН: {auto_tin}. Використовуйте логін для входу.', 'success')
        else:
            # Повідомлення суто для адміна
            flash('Адміністратора системи успішно зареєстровано!', 'success')

        db.session.commit()
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)


@main.route('/admin/history')
@login_required
def admin_history():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin_history.html', logs=logs)