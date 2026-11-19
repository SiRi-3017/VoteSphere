from getpass import getpass

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    user = db.session.query(User).filter_by(
        email="testvoter@example.com"
    ).first()

    if user is None:
        print("Account not found.")
    else:
        password = getpass("Enter a new password: ")
        confirm = getpass("Confirm the password: ")

        if len(password) < 8:
            print("Password must be at least 8 characters.")
        elif password != confirm:
            print("Passwords do not match.")
        else:
            user.set_password(password)
            db.session.commit()

            print("Password updated:", user.check_password(password))