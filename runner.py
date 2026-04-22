from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from forms import TaxpayerForm, TaxRecordForm
import csv
from io import StringIO
from flask import make_response
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:masterkey@127.0.0.1:5432/taxes_db'
app.config['SECRET_KEY'] = 'your_very_secret_key_123'

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Моделі
class Taxpayer(db.Model):
    __tablename__ = 'taxpayers'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    tin = db.Column(db.String(10), unique=True, nullable=False)
    records = db.relationship('TaxRecord', backref='taxpayer', lazy=True, cascade="all, delete-orphan")


class TaxType(db.Model):
    __tablename__ = 'tax_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    records = db.relationship('TaxRecord', backref='tax_type', lazy=True)


class TaxRecord(db.Model):
    __tablename__ = 'tax_records'
    id = db.Column(db.Integer, primary_key=True)
    taxpayer_id = db.Column(db.Integer, db.ForeignKey('taxpayers.id'), nullable=False)
    tax_type_id = db.Column(db.Integer, db.ForeignKey('tax_types.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime, nullable=True)


from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False) # Поле для хешу
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Методи для безпечної роботи з паролями
    def set_password(self, password):
        self.password_hash = generate_password_hash(password) # Хешування

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) # Перевірка

# Маршрути
@app.route('/')
def index():
    # 1. Запитуємо дані з бази через SQLAlchemy
    taxpayers = Taxpayer.query.all()
    records = TaxRecord.query.all()
    # ОСЬ ЦЕЙ РЯДОК ОТРИМУЄ ТІ 3 ЗАПИСИ, ЯКІ ТИ БАЧИШ У pgAdmin:
    tax_types = TaxType.query.all()

    # 2. Створюємо форми
    tp_form = TaxpayerForm()
    tr_form = TaxRecordForm()

    # 3. Якщо ти використовуєш поля WTForms (tr_form.tax_type_id),
    # обов'язково заповни їх варіантами вибору:
    tr_form.taxpayer_id.choices = [(t.id, t.full_name) for t in taxpayers]
    tr_form.tax_type_id.choices = [(tt.id, f"{tt.name} ({tt.rate}%)") for tt in tax_types]

    # 4. ПЕРЕДАЧА В ШАБЛОН (Перевір назву tax_types=tax_types)
    return render_template('index.html',
                           taxpayers=taxpayers,
                           records=records,
                           tax_types=tax_types,
                           tp_form=tp_form,
                           tr_form=tr_form,
                           user={'username': 'USER', 'is_superuser': True},
                           total_unpaid=0)


# 1. Додавання типу податку
@app.route('/taxtype/add', methods=['POST'])
def taxtype_add():
    name = request.form.get('name')
    rate = request.form.get('rate')
    if name and rate:
        new_type = TaxType(name=name, rate=float(rate))
        db.session.add(new_type)
        db.session.commit()
        flash('Нову ставку податку збережено!', 'success')
    return redirect(url_for('index'))


# 2. Редагування платника (те, що викликає JS у модалці)
@app.route('/taxpayer/edit/<int:pk>', methods=['POST'])
def taxpayer_edit(pk):
    tp = Taxpayer.query.get_or_404(pk)
    tp.full_name = request.form.get('full_name')

    # Оновлюємо ІПН тільки якщо поле було у формі і воно не порожнє
    new_tin = request.form.get('tin')
    if new_tin:
        tp.tin = new_tin

    db.session.commit()
    flash('Дані платника оновлено!', 'success')
    return redirect(url_for('index'))


# 3. Додавання нарахування (Журнал нарахувань)
@app.route('/record/add', methods=['POST'])
def taxrecord_add():
    tp_id = request.form.get('taxpayer_id')
    tt_id = request.form.get('tax_type_id')
    income = float(request.form.get('income'))

    # Отримуємо ставку податку для розрахунку
    tax_type = TaxType.query.get(tt_id)
    amount = income * (tax_type.rate / 100)

    new_record = TaxRecord(taxpayer_id=tp_id, tax_type_id=tt_id, amount=amount)
    db.session.add(new_record)
    db.session.commit()
    flash('Нарахування розраховано та додано!', 'success')
    return redirect(url_for('index'))


@app.route('/record/edit/<int:pk>', methods=['POST'])
def record_edit(pk):
    record = TaxRecord.query.get_or_404(pk)

    # Отримуємо дані з форми (імена полів мають збігатися з тими, що в JS)
    tp_id = request.form.get('taxpayer')
    tt_id = request.form.get('tax_type')
    income = request.form.get('income')

    if income:
        # Отримуємо нову ставку податку для перерахунку суми
        tax_type = TaxType.query.get(tt_id)

        record.taxpayer_id = tp_id
        record.tax_type_id = tt_id
        # Перераховуємо суму на основі нового доходу
        record.amount = float(income) * (tax_type.rate / 100)

        db.session.commit()
        flash('Нарахування успішно оновлено та перераховано!', 'success')

    return redirect(url_for('index'))

# 4. Видалення нарахування
@app.route('/record/delete/<int:pk>')
def taxrecord_delete(pk):
    record = TaxRecord.query.get_or_404(pk)
    db.session.delete(record)
    db.session.commit()
    flash('Запис видалено.', 'info')
    return redirect(url_for('index'))


@app.route('/taxpayer/add', methods=['POST'])
def taxpayer_add():
    form = TaxpayerForm()
    if form.validate_on_submit():
        new_tp = Taxpayer(full_name=form.full_name.data, tin=form.tin.data)
        db.session.add(new_tp)
        db.session.commit()
        flash('Платника успішно додано!', 'success')
    return redirect(url_for('index'))


@app.route('/taxpayer/delete/<int:pk>')
def taxpayer_delete(pk):
    tp = Taxpayer.query.get_or_404(pk)
    db.session.delete(tp)
    db.session.commit()
    flash('Платника видалено.', 'warning')
    return redirect(url_for('index'))


# --- ФУНКЦІЯ ОПЛАТИ (Pay Tax) ---
@app.route('/pay/<int:record_id>')
def pay_tax(record_id):
    record = TaxRecord.query.get_or_404(record_id)
    record.is_paid = True
    record.paid_at = datetime.utcnow()
    db.session.commit()
    flash(f'Податок на суму {record.amount} грн успішно сплачено!', 'success')
    return redirect(url_for('index'))


# --- ЕКСПОРТ У CSV ---
@app.route('/export-csv')
def export_taxpayers_csv():
    si = StringIO()

    # 1. Додаємо мітку BOM, щоб Excel зрозумів, що це UTF-8
    si.write('\ufeff')

    # 2. Вказуємо delimiter=';', щоб дані розбилися по колонках
    cw = csv.writer(si, delimiter=';')

    cw.writerow(['ID', 'ПІБ Платника', 'ІПН', 'Сума податку', 'Статус'])

    records = TaxRecord.query.all()
    for r in records:
        cw.writerow([
            r.id,
            r.taxpayer.full_name,
            r.taxpayer.tin,
            f"{r.amount:.2f}",  # Форматуємо число
            'Сплачено' if r.is_paid else 'Борг'
        ])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=tax_report.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    return output


# --- ГЕНЕРАЦІЯ КВИТАНЦІЇ (Simple Text/PDF) ---
@app.route('/receipt/<int:pk>')
def download_receipt(pk):
    record = TaxRecord.query.get_or_404(pk)
    if not record.is_paid:
        flash("Квитанція доступна тільки після оплати!", "danger")
        return redirect(url_for('index'))

    receipt_text = f"""
    ДЕРЖАВНА ПОДАТКОВА СЛУЖБА УКРАЇНИ
    КВИТАНЦІЯ ПРО ОПЛАТУ №{record.id}
    ----------------------------------
    Платник: {record.taxpayer.full_name}
    ІПН: {record.taxpayer.tin}
    Тип податку: {record.tax_type.name}
    Сума: {record.amount} грн
    Дата оплати: {record.paid_at.strftime('%Y-%m-%d %H:%M:%S')}
    ----------------------------------
    Дякуємо за вчасну сплату податків!
    """
    response = make_response(receipt_text)
    response.headers["Content-Disposition"] = f"attachment; filename=receipt_{pk}.txt"
    response.headers["Content-type"] = "text/plain"
    return response


# --- ПОДАТИ ДЕКЛАРАЦІЮ (User Side) ---
@app.route('/declare', methods=['POST'])
def declare_tax():
    # Оскільки ми в mock-режимі, беремо першого платника як "поточного користувача"
    current_tp = Taxpayer.query.first()
    if not current_tp:
        flash("Спочатку зареєструйте платника!", "danger")
        return redirect(url_for('index'))

    tt_id = request.form.get('tax_type_id')
    income = float(request.form.get('income'))
    tax_type = TaxType.query.get(tt_id)

    amount = income * (tax_type.rate / 100)
    new_record = TaxRecord(taxpayer_id=current_tp.id, tax_type_id=tt_id, amount=amount)
    db.session.add(new_record)
    db.session.commit()
    flash('Декларацію подано. Очікуйте нарахування в журналі.', 'success')
    return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    # Логіка виходу
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)