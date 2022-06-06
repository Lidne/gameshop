import datetime
import sqlalchemy
from sqlalchemy import orm, Column
from database import Base
import schemas
# from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from hashlib import md5
from passlib.context import CryptContext
"""Класс-модель пользователя для базы данных"""


class User(Base, SerializerMixin):
    __tablename__ = 'users'
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    id = Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    nick = Column(sqlalchemy.VARCHAR(255), nullable=False)
    email = Column(sqlalchemy.VARCHAR(255),
                              index=True, unique=True, nullable=True)
    hashed_password = Column(sqlalchemy.Text, nullable=True)
    modified_date = Column(sqlalchemy.DateTime,
                                      default=datetime.datetime.now)
    is_admin = Column(sqlalchemy.Boolean, default=False)

    comment = orm.relation("Comment")

    def set_password(self, password):
        self.hashed_password = self.pwd_context.hash(password)

    def check_password(self, password):
        return self.pwd_context.verify(password, self.hashed_password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def comavatar(self, size):
        digest = md5(self.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def to_schema(self):
        return schemas.User(**self.to_dict())


class Genre(Base, SerializerMixin):
    __tablename__ = 'genres'

    id = Column(sqlalchemy.Integer, nullable=False,
                           primary_key=True, autoincrement=True)
    genre = Column(sqlalchemy.VARCHAR(255), nullable=False)
    games = orm.relation('Game')


class Game(Base, SerializerMixin):
    __tablename__ = 'games'

    id = Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    price = Column(sqlalchemy.Integer, nullable=False)
    game_title = Column(sqlalchemy.VARCHAR(255), nullable=False)
    game_description = Column(sqlalchemy.Text, nullable=True)
    developers = Column(sqlalchemy.VARCHAR(255), nullable=True)
    release_date = Column(sqlalchemy.VARCHAR(255), nullable=True)
    ratio = Column(sqlalchemy.Float, nullable=True)
    is_selling = Column(sqlalchemy.Boolean, default=True)
    genre = Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("genres.id"), nullable=False)
    img = Column(sqlalchemy.Text, nullable=True)
    img_wide = Column(sqlalchemy.Text, nullable=True)

    genres = orm.relation("Genre", back_populates='games')
    comment = orm.relation("Comment")


class Comment(Base, SerializerMixin):
    __tablename__ = 'comments'

    id = Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    body = Column(sqlalchemy.Text, nullable=False)
    timestamp = Column(sqlalchemy.DateTime, nullable=False, default=datetime.datetime.now)
    user_id = Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
    game_id = Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('games.id'), nullable=False)

    games = orm.relation("User", back_populates='comment')
    users = orm.relation("Game", back_populates='comment')