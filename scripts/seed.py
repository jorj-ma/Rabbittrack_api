"""
Creates one farm, one admin account, and a couple of global breeds/sections —
enough to log in and start clicking around immediately.

Run after migrations are applied:
    python -m scripts.seed
"""

from app import create_app
from app import db
from app.models import Farm, User, FarmUser, FarmRole, Breed, Section, generate_farm_code

FARM_NAME = "Teule"

def run():
    app = create_app()
    with app.app_context():
        if Farm.query.filter_by(name=FARM_NAME).first():
            print(f"'{FARM_NAME}' already exists — skipping seed.")
            return

        code = generate_farm_code()
        farm = Farm(name=FARM_NAME, code=code)
        db.session.add(farm)
        db.session.flush()  # assigns farm.id

        users_to_seed = [
            {"name":"Anzigale George", "email": "anziegeorge4@gmail.com", "password": "admin123", "role": FarmRole.ADMIN},
            {"name": "Faith Bosire", "email": "f@gmail.com", "password": "password123", "role": FarmRole.ADMIN}        ]

        seeded_users = []
        for user_data in users_to_seed:
            user = User.query.filter_by(email=user_data["email"].lower()).first()
            if not user:
                user = User(name=user_data["name"], email=user_data["email"].lower())
                user.set_password(user_data["password"])
                db.session.add(user)
                db.session.flush()

            # Link user to the farm with their designated role
            db.session.add(FarmUser(farm_id=farm.id, user_id=user.id, role=user_data["role"]))
            seeded_users.append((user_data["email"], user_data["password"], user_data["role"]))

        db.session.add_all(
            [
                Breed(farm_id=None, name="New Zealand White", expected_weight_min_kg=4.0, expected_weight_max_kg=6.5),
                Breed(farm_id=None, name="Chinchilla", expected_weight_min_kg=1.4, expected_weight_max_kg=1.8),
                Breed(farm_id=None, name="Flemish Giant", expected_weight_min_kg=6.0, expected_weight_max_kg=10.0),
                Section(farm_id=farm.id, code="A-1", capacity=4),
                Section(farm_id=farm.id, code="B-2", capacity=4),
            ]
        )

        db.session.commit()

        print("Seed complete.")
        print(f" Farm '{FARM_NAME}' created with code: {code}")
        print(" Seeded users:")
        for email, password, role in seeded_users:
            print(f"  - {email} / {password} / {role.name}")

if __name__ == "__main__":
    run()
