import os
import string
import Levenshtein
from datetime import datetime, timedelta
from random import shuffle
from forms import CommentForm, GameForm, LoginForm, RegisterForm, SearchForm
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import FastAPI, Depends, HTTPException, Header, Response, status, Form, Request, Cookie
from fastapi.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from database import init_db, get_db
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from starlette_wtf import CSRFProtectMiddleware, csrf_protect
import schemas
import models

SECRET_KEY = "eea9bdbcb7dc5c45b72c8703138a09e1a6edb04f3579ad76b0fa7b64fd1eec2f"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
init_db()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return templates.TemplateResponse('error.html', {"request": request, "error": str(exc),
    "code": 500})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 401:
        return templates.TemplateResponse('unauthorised.html', {"request": request})
    return templates.TemplateResponse('error.html', {"request": request, "error": str(exc.detail),
    "code": exc.status_code})


def get_user(db: Session, username: str):
    user = db.query(models.User).filter(models.User.email == username).first()
    return user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not user.check_password(password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_token(access_token: str | None = Cookie(default=None)):
    return access_token


async def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)):
    if token is None:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not bebra",
                headers={"WWW-Authenticate": "Bearer"},
            )
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError as e:
        print(e)
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    return user


def get_cart(request: Request):
    cart = request.session.get('cart')
    if cart is None:
        return request.session.update(cart=[])
    return cart


@app.get("/", response_class=HTMLResponse)
@app.post("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    games = db.query(models.Game).filter(models.Game.is_selling == True).all()
    spin_games = list(filter(lambda x: x.img_wide is not None, games))
    home_games = list(filter(lambda x: x.img is not None, games))
    shuffle(spin_games)
    shuffle(home_games)
    return templates.TemplateResponse('index.html', {"request": request, "spin_games": spin_games[:3],
                                                     "home_games": home_games[:4], "current_user": current_user})


@app.post("/login", response_class=RedirectResponse)
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=access_token)
    return "/"


@app.get("/login", response_class=HTMLResponse)
async def login_html(request: Request, current_user: models.User = Depends(get_current_user)):
    form = await LoginForm.from_formdata(request)
    return templates.TemplateResponse('login.html', {"request": request, "current_user": current_user, "form": form})


@app.get("/profile", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user.to_schema()


@app.post("/register", response_class=RedirectResponse)
@app.get("/register", response_class=HTMLResponse)
async def register(request: Request, db: Session = Depends(get_db)):
    # TODO: регистрация через wtforms
    form = await RegisterForm.from_formdata(request)
    # if form.password != form.password_again:
    #    return templates.TemplateResponse('register.html', {"request": request, "current_user": None, "errors": ["Пароли не совпадают"]})
    if await form.validate_on_submit():
        user = get_user(db, form.email.data)
        if user:
            return templates.TemplateResponse('register.html', {"request": request, "current_user": None, "form": form,
                                                                "errors": ["Такой аккаунт уже зарегестрирован"]})
        user_db = models.User(
            nick=form.nick.data,
            email=form.email.data
        )
        user_db.set_password(form.password.data)
        db.add(user_db)
        db.commit()
        authenticate_user(db, form.email.data, form.password.data)
        return "/"
    return templates.TemplateResponse('register.html', {"request": request, "current_user": None, "form": form})


@app.get("/logout", response_class=RedirectResponse)
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return "/login"


@app.get("/games/{game_id}", response_class=HTMLResponse)
@app.post("/games/{game_id}", response_class=HTMLResponse)
async def game(request: Request, game_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_user), cart: set | None = Depends(get_cart)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()

    if game is None or (not game.is_selling and not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game with such id"
        )
    if cart is not None:
        in_cart = str(game_id) in cart
    else:
        in_cart = False
    genre = db.query(models.Genre).filter(
        models.Genre.id == game.genre).first()
    comments = db.query(models.Comment).filter(
        models.Comment.game_id == game_id).order_by(models.Comment.timestamp).all()
    for i in comments:
        i.username = db.query(models.User.nick).filter(
            models.User.id == i.user_id).first()[0]
        i.emailcom = db.query(models.User.email).filter(
            models.User.id == i.user_id).first()[0]
        i.avatarcom = models.User.comavatar(i.emailcom, 40)
    return templates.TemplateResponse('product.html', {"request": request, "game": game, "comments": comments,
                                                       "genre": genre, "current_user": current_user, "in_cart": in_cart})


@app.get("/add_game", response_class=HTMLResponse)
@app.post("/add_game", response_class=RedirectResponse)
@csrf_protect
async def some(request: Request, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    form = await GameForm.from_formdata(request)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access is denied",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account does not have admin rights"
        )
    if await form.validate_on_submit():
        if form.img.data is not None:
            file_path = 'img/covers/' + form.img.data.filename
            if os.access(file_path, os.F_OK):
                return templates.TemplateResponse('add_game.html', {"request": request, "error": "Обложка уже есть",
                                                                    "form": form, "current_user": current_user})
        else:
            file_path = None

        if form.img_wide.data is not None:
            file_path_wide = 'img/wide/' + form.img_wide.data.filename
            if os.access(file_path_wide, os.F_OK):
                return templates.TemplateResponse('add_game.html', {"request": request, "error": "Широкая картинка уже есть",
                                                                    "form": form, "current_user": current_user})
        else:
            file_path_wide = None

        game = models.Game(
            game_title=form.name.data,
            ratio=form.ratio.data,
            price=int(form.price.data),
            game_description=form.description.data,
            developers=form.developers.data,
            release_date=form.release_date.data,
            genre=int(form.genre.data),
            img=file_path,
            img_wide=file_path_wide
        )
        db.add(game)
        db.commit()

        path = "/games/" + \
            str(db.query(models.Game.id).filter(
                models.Game.game_title == game.game_title).first()[0])

        with open(file_path, mode='wb') as file:
            content = form.img.data.read()
            file.write(content)

        with open(file_path_wide, mode='wb') as file_wide:
            content = form.img_wide.data.read()
            file_wide.write(content)

        return path

    return templates.TemplateResponse('add_game.html', {"request": request, "current_user": current_user, "form": form})


@app.get("/delete_game/{game_id}", response_class=RedirectResponse)
async def delete_game(request: Request, game_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user does not have admin rigths"
        )
    game_query = db.query(models.Game).where(models.Game.id == game_id)
    game = game_query.first()
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game with such id"
        )
    if game is not None and not game.is_selling:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Game already is not selling"
        )
    game_query.update({models.Game.is_selling: False})
    db.commit()
    return "/games/" + str(game_id)


@app.get("/add_game/{game_id}", response_class=RedirectResponse)
async def set_selling_game(game_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user does not have admin rigths"
        )
    game_query = db.query(models.Game).where(models.Game.id == game_id)
    game = game_query.first()
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game with such id"
        )
    if game is not None and game.is_selling:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Game already is selling"
        )
    game_query.update({models.Game.is_selling: True})
    db.commit()
    return "/games/" + str(game_id)


@app.get("/list")
async def game_list(request: Request, search: str | None = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if search is not None:
        matched_games = db.query(models.Game).where(
            models.Game.game_title.contains(search)).all()
        matched_games.sort(
            key=lambda x: Levenshtein.distance(search, x.game_title))
        return templates.TemplateResponse('list.html', {"request": request, "games_list": matched_games, "current_user": current_user})
    games = db.query(models.Game).where((models.Game.is_selling == True) & (models.Game.img is not None)) \
        .order_by(models.Game.game_title).all()

    return templates.TemplateResponse('list.html', {"request": request, "games_list": games, "current_user": current_user})


@app.get("/add_comment/{game_id}", response_class=HTMLResponse)
@app.post("/add_comment/{game_id}", response_class=RedirectResponse, status_code=302)
async def add_comment(request: Request, game_id: int, db: Session = Depends(get_db), current_user: Session = Depends(get_current_user)):
    form = await CommentForm.from_formdata(request)
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    if request.method == "POST":
        comment = models.Comment(
            body=form.body.data,
            user_id=current_user.id,
            game_id=game_id
        )
        print(comment)
        db.add(comment)
        db.commit()
        return "/games/" + str(game_id)
    return templates.TemplateResponse("comments.html", {"request": request, "form": form, "current_user": current_user, "game_id": game_id})


@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request, cart: list | None = Depends(get_cart),
               current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if cart is None:
        return templates.TemplateResponse('cart.html', {"request": request, "current_user": current_user, "cart_list": []})
    cart_list = db.query(models.Game).filter(models.Game.id.in_(cart)).all()
    return templates.TemplateResponse('cart.html', {"request": request, "current_user": current_user, "cart_list": cart_list})


@app.get("/cart_add/{game_id}", response_class=RedirectResponse)
async def cart_add(request: Request, response: Response, game_id: int):
    cart_list = request.session.get("cart")
    if cart_list is None or type(cart_list) != list:
        request.session.update(cart=[])
    cart_list.append(game_id)
    request.session.update(cart=list(cart_list))
    print(request.session.get("cart"))
    return "/cart"


@app.get("/cart_delete/{game_id}", response_class=RedirectResponse)
async def cart_delete(request: Request, response: Response, game_id: int):
    cart_list = request.session.get("cart")
    if cart_list is None:
        return "/games/" + str(game_id)
    if game_id == 0 or type(cart_list) != list:
        request.session.update(cart=[])
        return "/cart"
    cart_list.pop(cart_list.index(game_id))
    if cart:
        request.session.update(cart=cart_list)
    else:
        request.session.update(cart=[])
    return "/cart"


@app.get("/buy", response_class=HTMLResponse)
async def buy(request: Request, current_user: models.User = Depends(get_current_user),
              db: Session = Depends(get_db), cart: list | None = Depends(get_cart)):
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    cart_list = db.query(models.Game).filter(models.Game.id.in_(cart)).all()
    total = sum(list(map(lambda x: x.price, cart_list)))
    return templates.TemplateResponse('payment.html', {"request": request, "current_user": current_user,
                                                       "cart_list": cart_list, "total": total})


@app.get("/goods")
async def goods(request: Request, response: Response, current_user: models.User = Depends(get_current_user),
                db: Session = Depends(get_db), cart_list: set | None = Depends(get_cart)):
    if current_user is None:
        raise  HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Restricted for unauthorized users"
        )
    games = db.query(models.Game).filter(models.Game.id.in_(cart_list)).all()

    text = list(string.ascii_uppercase + string.digits)
    for i in range(len(games)):
        shuffle(text)
        games[i].code = ''.join(text[:7])
    request.session.update(cart=[])
    return templates.TemplateResponse('goods.html', {"request": request, "current_user": current_user, "games": games})


@app.get("/test/")
async def test():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Иди нахуй"
    )
