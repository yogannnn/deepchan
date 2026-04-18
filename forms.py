from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField
from flask_wtf.file import MultipleFileField, FileAllowed
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from flask import current_app, session

def allowed_extensions_validator():
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', ['jpg', 'jpeg', 'png', 'gif'])
    return FileAllowed(allowed, 'Недопустимый формат')

class PostForm(FlaskForm):
    name = StringField('Имя', validators=[Optional(), Length(max=80)], default='Аноним')
    subject = StringField('Тема', validators=[Optional(), Length(max=200)])
    comment = TextAreaField('Комментарий', validators=[DataRequired()])
    files = MultipleFileField('Картинки (до 4)', validators=[Optional()])
    sage = BooleanField('Sage (не поднимать тред)')
    password = PasswordField('Пароль (для удаления)', validators=[Optional()])
    captcha_answer = StringField('Капча', validators=[Optional()])
    submit = SubmitField('Отправить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files.validators.append(allowed_extensions_validator())

    def validate_captcha_answer(self, field):
        if current_app.config.get('CAPTCHA_ENABLED', False):
            if field.data != session.get('captcha_text', ''):
                raise ValidationError('Неверный код с картинки.')
            session.pop('captcha_text', None)
