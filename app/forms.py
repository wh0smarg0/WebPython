from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from .models import User

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

class RegistrationForm(FlaskForm):
    """Форма для створення нового акаунта"""
    name = StringField('Повне ім\'я', validators=[DataRequired(), Length(max=100)])
    username = StringField('Логін', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Підтвердіть пароль',
                                    validators=[DataRequired(), EqualTo('password', message='Паролі повинні збігатися')])
    submit = SubmitField('Зареєструватися')

    # Додаткова перевірка, щоб не було дублікатів у базі
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Цей логін уже зайнятий.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Цей Email уже зареєстрований.')