from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.user import AccountDelete, PasswordChange, Token, UserCreate, UserOut, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["autenticación"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    user = User(email=email, full_name=data.full_name, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    # OAuth2PasswordRequestForm usa el campo "username"; aquí contiene el correo.
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user

@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, db: DbSession, user: CurrentUser):
    user.full_name = data.full_name
    db.commit()
    db.refresh(user)
    return user

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChange, db: DbSession, user: CurrentUser):
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual es incorrecta")
    if data.current_password == data.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La nueva contraseña debe ser distinta de la actual")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(data: AccountDelete, db: DbSession, user: CurrentUser):
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña es incorrecta")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)