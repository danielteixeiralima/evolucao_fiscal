from app import create_app, db
from models import *

app = create_app()

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables with new schema...")
    db.create_all()
    print("Database schema reset successfully!")
