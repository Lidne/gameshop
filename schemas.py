from pydantic import BaseModel
from datetime import datetime


class UserBase(BaseModel):
    nick: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    hashed_password: str
    is_admin: bool
    modified_date: datetime

    class Config:
        orm_mode = True


class GenreBase(BaseModel):
    genre: str


class Genre(GenreBase):
    id: int
    
    class Config:
        orm_mode = True


class GameBase(BaseModel):
    price: int
    name: str
    description: str
    developers: str
    release_date: str
    ratio: float
    is_selling: bool
    genre: int
    img: str
    img_wide: str


class GameCreate(GameBase):
    pass


class Game(GameBase):
    id: int

    class Config:
        orm_mode = True


class CommentBase(BaseModel):
    body: str
    user_id: int
    game_id: int


class CommentCreate(CommentBase):
    pass


class Comment(CommentBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str