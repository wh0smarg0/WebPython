from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class TaxpayerForm(FlaskForm):
    full_name = StringField('ПІБ Платника',
                           validators=[DataRequired(), Length(min=3, max=255)],
                           render_kw={"class": "form-control", "placeholder": "ПІБ"})
    tin = StringField('ІПН',
                     validators=[DataRequired(), Length(min=10, max=10)],
                     render_kw={"class": "form-control", "placeholder": "10 цифр"})
    submit = SubmitField('Додати')

class TaxRecordForm(FlaskForm):
    taxpayer_id = SelectField('Платник', coerce=int, validators=[DataRequired()], render_kw={"class": "form-select"})
    tax_type_id = SelectField('Тип податку', coerce=int, validators=[DataRequired()], render_kw={"class": "form-select"})
    income = FloatField('Дохід', validators=[DataRequired()], render_kw={"class": "form-control"})
    submit = SubmitField('Розрахувати')