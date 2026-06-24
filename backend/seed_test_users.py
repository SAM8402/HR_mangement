import asyncio
from datetime import date
from sqlalchemy import select
from app.db.session import async_session
from app.models.user import User
from app.models.department import Department
from app.models.leave import LeaveType, LeaveBalance
from app.core.security import hash_password

async def main():
    print("Connecting to database...")
    async with async_session() as db:
        # 1. Get or create a default department
        result = await db.execute(select(Department).where(Department.name == "Engineering"))
        dept = result.scalar_one_or_none()
        if not dept:
            dept = Department(name="Engineering")
            db.add(dept)
            await db.flush()
            print("   Created 'Engineering' department.")
        else:
            print("   Using existing 'Engineering' department.")

        # 2. Check for seeded leave types
        result = await db.execute(select(LeaveType))
        leave_types = result.scalars().all()
        if not leave_types:
            print("   Error: No leave types found in database.")
            print("   Please start your backend server (python main.py) at least once first to auto-seed leave types!")
            return

        # Define users to add
        users_data = [
            {"name": "Alice HR", "email": "alice_hr@test.com", "role": "hr"},
            {"name": "Bob Employee", "email": "bob_emp@test.com", "role": "employee"},
            {"name": "Charlie Employee", "email": "charlie_emp@test.com", "role": "employee"},
        ]

        print("\nSeeding users:")
        for udata in users_data:
            # Check if user already exists
            res = await db.execute(select(User).where(User.email == udata["email"]))
            existing_user = res.scalar_one_or_none()
            if existing_user:
                print(f" - User {udata['email']} already exists. Skipping.")
                continue

            # Create User
            user = User(
                name=udata["name"],
                email=udata["email"],
                password_hash=hash_password("password123"),
                role=udata["role"],
                joining_date=date.today(),
                is_active=True,
                department_id=dept.id
            )
            db.add(user)
            await db.flush()
            print(f" - Added {udata['role'].upper()}: {udata['name']} ({udata['email']})")

            # Seed leave balances
            for lt in leave_types:
                if lt.name == "unpaid":
                    continue
                balance = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=lt.id,
                    year=date.today().year,
                    total_days=lt.days_per_year,
                    used_days=0,
                    remaining_days=lt.days_per_year
                )
                db.add(balance)
            await db.flush()
            print(f"   Seeded leave balances for {udata['name']}")

        await db.commit()
        print("\nAll database updates committed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
