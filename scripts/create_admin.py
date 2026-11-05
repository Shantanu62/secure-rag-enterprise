import getpass
import sys
from sqlalchemy.exc import SQLAlchemyError
from backend.auth.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from backend.database.connection import SessionLocal
def main():
    print("\n=== Create Secure RAG Admin Account ===")
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip()
    if len(username) < 3:
        print("Error: Username must contain at least 3 characters.")
        sys.exit(1)
    if "@" not in email or "." not in email:
        print("Error: Enter a valid email address.")
        sys.exit(1)
    password = getpass.getpass("Admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        print("Error: Password must contain at least 12 characters.")
        sys.exit(1)
    if password != confirm_password:
        print("Error: Passwords do not match.")
        sys.exit(1)
    db = SessionLocal()
    try:
        if get_user_by_username(db, username):
            print("Error: Username already exists.")
            sys.exit(1)
        if get_user_by_email(db, email):
            print("Error: Email already exists.")
            sys.exit(1)
        user = create_user(
            db=db,
            username=username,
            email=email,
            password=password,
            role="Admin",
        )
        print("\nAdmin account created successfully.")
        print(f"User ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Role: {user.role}")
    except (ValueError, SQLAlchemyError):
        db.rollback()
        print("Error: Admin account could not be created.")
        sys.exit(1)
    finally:
        db.close()
if __name__ == "__main__":
    main()
