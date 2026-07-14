from app import app
from models import db, User

with app.app_context():

    admin = User.query.filter_by(email="admin@gmail.com").first()

    if admin:
        print("Admin already exists!")

    else:
        admin = User(
            name="Admin",
            email="admin@gmail.com",
            password="admin123",
            role="Admin"
        )

        db.session.add(admin)
        db.session.commit()

        print("Admin account created successfully!")