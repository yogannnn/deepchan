from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import MultipleFileField
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional


class PostForm(FlaskForm):
    name = StringField("Имя", validators=[Optional(), Length(max=80)], default="Аноним")
    subject = StringField("Тема", validators=[Optional(), Length(max=200)])
    comment = TextAreaField("Комментарий", validators=[Optional()])
    files = MultipleFileField("Картинки", validators=[Optional()])
    sage = BooleanField("Sage (не поднимать тред)")
    password = PasswordField("Пароль (для удаления)", validators=[Optional()])
    captcha_answer = StringField("Капча", validators=[Optional()])
    submit = SubmitField("Отправить")
