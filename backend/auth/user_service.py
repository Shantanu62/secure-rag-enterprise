from sqlalchemy.orm import Session
from backend.auth.permissions import Role
from backend.auth.security import hash_password, verify_password
from backend.models.user import User
def get_user_by_username(db: Session, username: str) -> User | None:
    """Retrieve a user by username."""
    return db.query(User).filter(User.username == username).first()
def get_user_by_email(db: Session, email: str) -> User | None:
    """Retrieve a user by email."""
    return db.query(User).filter(User.email == email).first()
def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: str = Role.EMPLOYEE.value,
) -> User:
    """Create a user with a securely hashed password."""
    if role not in {item.value for item in Role}:
        raise ValueError("Invalid user role")
    if get_user_by_username(db, username):
        raise ValueError("Username already exists")
    if get_user_by_email(db, email):
        raise ValueError("Email already exists")
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    """Authenticate an active user using their stored password hash."""
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
