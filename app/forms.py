from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DecimalField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    """Форма для входу в систему"""
    username = StringField('Логін', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запам\'ятати мене')
    submit = SubmitField('Увійти')

class TaxpayerForm(FlaskForm):
    """Форма для додавання/редагування платника"""
    full_name = StringField('ПІБ платника', validators=[DataRequired(), Length(max=100)])
    tin = StringField('ІПН (10 цифр)', validators=[DataRequired(), Length(min=10, max=10)])
    submit = SubmitField('Зберегти')

class TaxRecordForm(FlaskForm):
    """Форма для створення нарахування податку"""
    # Поля SelectField ми заповнюємо даними (choices) динамічно у views.py
    taxpayer_id = SelectField('Платник', coerce=int, validators=[DataRequired()])
    tax_type_id = SelectField('Тип податку', coerce=int, validators=[DataRequired()])
    income = DecimalField('Сума доходу (грн)', validators=[DataRequired()])
    submit = SubmitField('Нарахувати')