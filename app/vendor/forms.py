# app/vendor/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, TextAreaField, FileField, FieldList, FormField
from wtforms.validators import DataRequired, Email


class VendorRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])


class ItemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    images = FieldList(FileField('Image', validators=[DataRequired()]), min_entries=1, max_entries=7)
