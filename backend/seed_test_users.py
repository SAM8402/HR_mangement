import asyncio
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.db.base import Base
from app.db.session import async_session, engine
from app.core.security import hash_password
# Ensure all models are imported so Base.metadata picks them up
from app.models import (Attendance, ChatFeedback, CompanyRole, CompanyRule,
                        Department, LeaveBalance, LeaveRequest, LeaveType,
                        User, WorkUpdate)


async def main():
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Connecting to database...")
    async with async_session() as db:
        # ── Departments ──────────────────────────────────────────────
        dept_result = await db.execute(select(Department))
        depts = {d.name: d for d in dept_result.scalars().all()}

        if "Engineering" not in depts:
            depts["Engineering"] = Department(name="Engineering")
            db.add(depts["Engineering"])
        if "HR" not in depts:
            depts["HR"] = Department(name="HR")
            db.add(depts["HR"])
        await db.flush()
        print("Departments ready.")

        # ── Leave Types ──────────────────────────────────────────────
        leave_types_data = [
            ("casual", 18, False, 5),
            ("sick", 12, False, 3),
            ("earned", 10, True, 10),
            ("paid", 40, False, 30),
            ("unpaid", 0, False, 0),
        ]
        existing_names = set()
        lt_result = await db.execute(select(LeaveType))
        for lt in lt_result.scalars().all():
            existing_names.add(lt.name)
        for name, days, carry, max_days in leave_types_data:
            if name not in existing_names:
                db.add(LeaveType(name=name, days_per_year=days, carry_forward=carry, max_consecutive_days=max_days))
        await db.flush()
        print("Leave types seeded.")
        lt_result = await db.execute(select(LeaveType))
        leave_types = {lt.name: lt for lt in lt_result.scalars().all()}
        if not leave_types:
            raise RuntimeError("No leave types found. Start backend first to auto-seed them.")

        # ── Users ───────────────────────────────────────────────────
        users_data = [
            {"name": "Admin User",   "email": "admin@hr.com",     "role": "admin",    "dept": None},
            {"name": "Alice HR",     "email": "alice_hr@test.com",       "role": "hr",        "dept": "HR"},
            {"name": "Mike Manager", "email": "mike_mgr@test.com",       "role": "manager",   "dept": "Engineering"},
            {"name": "Bob Employee", "email": "bob_emp@test.com",        "role": "employee",  "dept": "Engineering"},
            {"name": "Charlie Employee", "email": "charlie_emp@test.com",    "role": "employee",  "dept": "Engineering"},
            {"name": "Diana Employee", "email": "diana_emp@test.com",       "role": "employee",  "dept": "HR"},
        ]

        existing_users = {}
        for ud in users_data:
            res = await db.execute(select(User).where(User.email == ud["email"]))
            u = res.scalar_one_or_none()
            if not u:
                u = User(
                    name=ud["name"],
                    email=ud["email"],
                    password_hash=hash_password("12345678"),
                    role=ud["role"],
                    joining_date=date(2024, 6, 1),
                    is_active=True,
                    department_id=depts.get(ud["dept"]).id if ud.get("dept") else None,
                )
                db.add(u)
                await db.flush()
                print(f"  Created {ud['role']}: {ud['name']} ({ud['email']})")
            existing_users[ud["role"]] = u

        # ── Leave Balances ──────────────────────────────────────────
        for user in existing_users.values():
            for lt in leave_types.values():
                if lt.name == "unpaid":
                    continue
                res = await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == user.id,
                        LeaveBalance.leave_type_id == lt.id,
                    )
                )
                if not res.scalar_one_or_none():
                    used = random.randint(0, max(0, lt.days_per_year - 5)) if lt.days_per_year > 0 else 0
                    db.add(LeaveBalance(
                        user_id=user.id,
                        leave_type_id=lt.id,
                        year=date.today().year,
                        total_days=lt.days_per_year,
                        used_days=used,
                        remaining_days=lt.days_per_year - used,
                    ))
        await db.flush()
        print("Leave balances seeded.")

        # ── Attendance (last 30 days) ───────────────────────────────
        today = date.today()
        statuses = ["present", "present", "present", "present", "present", "late", "late", "half_day", "wfh", "absent"]

        for role_key, user in existing_users.items():
            if role_key in ("admin",):
                continue
            for days_ago in range(30):
                d = today - timedelta(days=days_ago)
                if d.weekday() >= 5:
                    continue  # skip weekends

                res = await db.execute(
                    select(Attendance).where(
                        Attendance.user_id == user.id, Attendance.date == d
                    )
                )
                if res.scalar_one_or_none():
                    continue

                status = random.choice(statuses)
                check_in = None
                check_out = None
                if status != "absent":
                    hour = 8 if random.random() > 0.3 else random.choice([9, 9, 10])
                    minute = random.randint(0, 59)
                    check_in = datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)
                    out_hour = hour + 8 + random.choice([0, 0, 1])
                    check_out = datetime(d.year, d.month, d.day, out_hour, random.randint(0, 59), tzinfo=timezone.utc)

                db.add(Attendance(
                    user_id=user.id,
                    date=d,
                    check_in=check_in,
                    check_out=check_out,
                    status=status,
                ))
        await db.flush()
        print("Attendance records seeded.")

        # ── Work Updates (last 2 weeks) ─────────────────────────────
        for role_key, user in existing_users.items():
            if role_key in ("admin",):
                continue
            for days_ago in range(14):
                d = today - timedelta(days=days_ago)
                if d.weekday() >= 5:
                    continue

                res = await db.execute(
                    select(WorkUpdate).where(
                        WorkUpdate.user_id == user.id, WorkUpdate.date == d
                    )
                )
                if res.scalar_one_or_none():
                    continue

                titles = [
                    "Worked on feature X", "Bug fixes", "Code review",
                    "Client meeting", "Documentation update", "Database optimization",
                    "UI improvements", "API integration", "Testing & QA",
                    "Sprint planning", "Team standup", "Research & learning",
                ]
                tags_pool = [
                    ["frontend", "react"], ["backend", "api"], ["bugfix"],
                    ["meeting", "client"], ["docs"], ["database"],
                    ["ui", "ux"], ["integration"], ["testing"],
                    ["planning"], ["standup"], ["research"],
                ]
                i = random.randrange(len(titles))
                db.add(WorkUpdate(
                    user_id=user.id,
                    title=titles[i],
                    description=f"Spent the day on {titles[i].lower()}. [Dummy data for testing]",
                    date=d,
                    tags=tags_pool[i],
                ))
        await db.flush()
        print("Work updates seeded.")

        # ── Leave Requests ──────────────────────────────────────────
        alice = existing_users.get("hr")
        mike = existing_users.get("manager")

        for role_key, user in existing_users.items():
            if role_key in ("admin", "hr", "manager"):
                continue
            if random.random() > 0.6:
                continue

            lt = random.choice([v for k, v in leave_types.items() if k != "unpaid"])
            from_d = today + timedelta(days=random.randint(5, 20))
            to_d = from_d + timedelta(days=random.randint(0, 2))
            status = random.choice(["pending", "approved", "rejected"])

            res = await db.execute(
                select(LeaveRequest).where(
                    LeaveRequest.applicant_id == user.id,
                    LeaveRequest.from_date == from_d,
                )
            )
            if res.scalar_one_or_none():
                continue

            db.add(LeaveRequest(
                applicant_id=user.id,
                approver_id=alice.id if status != "pending" else None,
                leave_type_id=lt.id,
                from_date=from_d,
                to_date=to_d,
                business_days=(to_d - from_d).days + 1,
                reason=f"[Seed] {lt.name} leave request for testing",
                status=status,
                rejection_reason="Needs more detail" if status == "rejected" else None,
            ))
        await db.flush()
        print("Leave requests seeded.")

        # ── Company Roles ────────────────────────────────────────────
        admin_user = existing_users.get("admin")
        sample_roles = [
            {"title": "Frontend Developer", "desc": "Builds UI components with React/Vue",
             "resp": "Develop and maintain frontend applications",
             "skills": ["JavaScript", "React", "CSS", "TypeScript"]},
            {"title": "Backend Developer", "desc": "Designs APIs and database schemas",
             "resp": "Build scalable backend services",
             "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"]},
        ]
        for r in sample_roles:
            res = await db.execute(select(CompanyRole).where(CompanyRole.title == r["title"]))
            if not res.scalar_one_or_none():
                db.add(CompanyRole(
                    title=r["title"],
                    description=r["desc"],
                    responsibilities=r["resp"],
                    required_skills=r["skills"],
                    created_by=admin_user.id,
                ))
        print("Company roles seeded.")

        # ── Company Rules ────────────────────────────────────────────
        sample_rules = [
            {"title": "Work from Home Policy",
             "content": "Employees may work from home up to 2 days per week with manager approval.",
             "category": "policy"},
            {"title": "Code of Conduct",
             "content": "All employees must follow the company code of conduct, respecting diversity and maintaining professionalism.",
             "category": "conduct"},
        ]
        for r in sample_rules:
            res = await db.execute(select(CompanyRule).where(CompanyRule.title == r["title"]))
            if not res.scalar_one_or_none():
                db.add(CompanyRule(
                    title=r["title"],
                    content=r["content"],
                    category=r["category"],
                    created_by=admin_user.id,
                    is_active=True,
                ))
        print("Company rules seeded.")

        # ── Commit ──────────────────────────────────────────────────
        await db.commit()
        print("\nAll dummy data seeded successfully!")
        print("Users & passwords:")
        for ud in users_data:
            print(f"  {ud['email']} / password123")


if __name__ == "__main__":
    asyncio.run(main())
