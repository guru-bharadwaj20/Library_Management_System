"""Authentication: student self-registration, librarian creation, login."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_librarian
from ..models import User
from ..schemas import Token, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_user(db: Session, payload: UserCreate, role: str) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already taken")
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_student(payload: UserCreate, db: Session = Depends(get_db)):
    """Open self-registration — always creates a student-role account."""
    return _create_user(db, payload, role="student")


@router.post(
    "/register-librarian",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_librarian(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_librarian),
):
    """Only an existing librarian may mint another librarian."""
    return _create_user(db, payload, role="librarian")


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token, role=user.role, username=user.username)
