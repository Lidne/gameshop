from starlette_wtf import StarletteForm
from models import Genre
from sqlalchemy.orm import Session
from database import get_db_, init_db
from wtforms import StringField, PasswordField, SelectField, SubmitField, IntegerField, TextAreaField, FileField, BooleanField
from wtforms.validators import DataRequired, Email, InputRequired, EqualTo
from wtforms.widgets import PasswordInput

init_db()
db: Session = get_db_()
genres = [tuple([str(i), j]) for i, j in db.query(Genre.id, Genre.genre).all()]


class GameForm(StarletteForm):
    name = StringField('Название', validators=[InputRequired()])
    price = IntegerField('Цена', validators=[InputRequired()])
    description = TextAreaField('Описание')
    developers = StringField('Разработчики', validators=[InputRequired()])
    release_date = StringField('Дата', validators=[InputRequired()])
    genre = SelectField(u'Жанр', validators=[InputRequired()], choices=genres)
    img = FileField('Изображение', validators=[DataRequired()])
    img_wide = FileField('Широкое изображение')
    ratio = IntegerField('Оценка', validators=[InputRequired()])
    submit = SubmitField('Добавить')


class RegisterForm(StarletteForm):
    nick = StringField('Имя', validators=[DataRequired()])
    email = StringField('Почта', validators=[InputRequired()])
    password = PasswordField('Пароль', widget=PasswordInput(hide_value=True),
                             validators=[InputRequired(), EqualTo('password_again', message='Пароли должны совпадать')])
    password_again = PasswordField(
        'Повторите пароль', validators=[InputRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Зарегестрироваться')


class LoginForm(StarletteForm):
    email = StringField('Логин', validators=[
                        Email(), DataRequired('Введите адрес почты')], name="username")
    password = PasswordField('Пароль', widget=PasswordInput(
        hide_value=True), validators=[InputRequired()], name="password")
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class SearchForm(StarletteForm):
    search = StringField('Введите название')
    submit = SubmitField('Искать')


class CommentForm(StarletteForm):
    body = TextAreaField('Комментарий', validators=[DataRequired()])
    submit = SubmitField('Комментировать')
