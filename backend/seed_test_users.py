"""Seed script for populating the database with test data.

Creates departments, leave types, users (admin / hr / manager /
employee across departments), leave balances, attendance records
for the last 30 days, work updates, leave requests, company roles
and rules, chat sessions with messages, and chat feedback.
All users share the password "12345678".
"""

import asyncio
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import async_session, engine
from app.models import (
    Attendance,
    ChatFeedback,
    ChatMessage,
    ChatSession,
    CompanyRole,
    CompanyRule,
    Department,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    User,
    WorkUpdate,
)


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
        if "Marketing" not in depts:
            depts["Marketing"] = Department(name="Marketing")
            db.add(depts["Marketing"])
        if "Finance" not in depts:
            depts["Finance"] = Department(name="Finance")
            db.add(depts["Finance"])
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
                db.add(
                    LeaveType(
                        name=name,
                        days_per_year=days,
                        carry_forward=carry,
                        max_consecutive_days=max_days,
                    )
                )
        await db.flush()
        print("Leave types seeded.")
        lt_result = await db.execute(select(LeaveType))
        leave_types = {lt.name: lt for lt in lt_result.scalars().all()}
        if not leave_types:
            raise RuntimeError(
                "No leave types found. Start backend first to auto-seed them."
            )

        # ── Users ───────────────────────────────────────────────────
        users_data = [
            {
                "name": "Admin User",
                "email": "admin@hr.com",
                "role": "admin",
                "dept": None,
                "image": "https://example.com/avatars/admin.png",
            },
            {
                "name": "Alice HR",
                "email": "alice_hr@test.com",
                "role": "hr",
                "dept": "HR",
                "image": "https://example.com/avatars/alice.png",
            },
            {
                "name": "Mike Manager",
                "email": "mike_mgr@test.com",
                "role": "manager",
                "dept": "Engineering",
                "image": "https://example.com/avatars/mike.png",
            },
            {
                "name": "Bob Employee",
                "email": "bob_emp@test.com",
                "role": "employee",
                "dept": "Engineering",
                "image": None,
            },
            {
                "name": "Charlie Employee",
                "email": "charlie_emp@test.com",
                "role": "employee",
                "dept": "Engineering",
                "image": None,
            },
            {
                "name": "Diana Employee",
                "email": "diana_emp@test.com",
                "role": "employee",
                "dept": "HR",
                "image": None,
            },
            {
                "name": "Eve Marketing",
                "email": "eve_mktg@test.com",
                "role": "employee",
                "dept": "Marketing",
                "image": "https://example.com/avatars/eve.png",
            },
            {
                "name": "Frank Finance",
                "email": "frank_fin@test.com",
                "role": "employee",
                "dept": "Finance",
                "image": None,
            },
        ]

        all_users = []
        existing_users = {}
        base_join_date = date(2023, 1, 15)
        for i, ud in enumerate(users_data):
            res = await db.execute(select(User).where(User.email == ud["email"]))
            u = res.scalar_one_or_none()
            if not u:
                u = User(
                    name=ud["name"],
                    email=ud["email"],
                    password_hash=hash_password("12345678"),
                    role=ud["role"],
                    joining_date=base_join_date + timedelta(days=30 * i),
                    profile_image=ud["image"],
                    is_active=True,
                    department_id=depts.get(ud["dept"]).id if ud.get("dept") else None,
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
                    + timedelta(days=i),
                )
                db.add(u)
                await db.flush()
                print(f"  Created {ud['role']}: {ud['name']} ({ud['email']})")
            existing_users[ud["role"]] = u
            all_users.append(u)

        # ── Department heads ─────────────────────────────────────────
        depts["Engineering"].head_user_id = existing_users["manager"].id
        depts["HR"].head_user_id = existing_users["hr"].id
        depts["Marketing"].head_user_id = existing_users.get(
            "employee", all_users[6]
        ).id
        depts["Finance"].head_user_id = existing_users.get("employee", all_users[7]).id
        await db.flush()
        print("Department heads assigned.")

        # ── Leave Balances ──────────────────────────────────────────
        for user in all_users:
            for lt in leave_types.values():
                if lt.name == "unpaid":
                    continue
                res = await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == user.id,
                        LeaveBalance.leave_type_id == lt.id,
                        LeaveBalance.year == date.today().year,
                    )
                )
                if not res.scalar_one_or_none():
                    used = (
                        random.randint(0, max(0, lt.days_per_year - 5))
                        if lt.days_per_year > 0
                        else 0
                    )
                    db.add(
                        LeaveBalance(
                            user_id=user.id,
                            leave_type_id=lt.id,
                            year=date.today().year,
                            total_days=lt.days_per_year,
                            used_days=used,
                            remaining_days=lt.days_per_year - used,
                        )
                    )
        await db.flush()
        print("Leave balances seeded.")

        # ── Attendance (last 30 days) ───────────────────────────────
        today = date.today()
        statuses = [
            "present",
            "present",
            "present",
            "present",
            "present",
            "late",
            "late",
            "half_day",
            "wfh",
            "absent",
        ]
        attendance_notes_pool = [
            None,
            None,
            None,
            "Arrived on time, productive day",
            "Completed sprint tasks ahead of schedule",
            "Had a team meeting in the morning",
            "Worked from home due to personal reasons",
            "Left early after completing deliverables",
            "Doctor appointment in the afternoon",
            "System outage delayed start",
        ]

        for user in all_users:
            if user.role == "admin":
                continue
            for days_ago in range(30):
                d = today - timedelta(days=days_ago)
                if d.weekday() >= 5:
                    continue

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
                    check_in = datetime(
                        d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc
                    )
                    out_hour = hour + 8 + random.choice([0, 0, 1])
                    check_out = datetime(
                        d.year,
                        d.month,
                        d.day,
                        out_hour,
                        random.randint(0, 59),
                        tzinfo=timezone.utc,
                    )

                db.add(
                    Attendance(
                        user_id=user.id,
                        date=d,
                        check_in=check_in,
                        check_out=check_out,
                        status=status,
                        notes=random.choice(attendance_notes_pool),
                        created_at=datetime(
                            d.year, d.month, d.day, 23, 0, 0, tzinfo=timezone.utc
                        ),
                    )
                )
        await db.flush()
        print("Attendance records seeded.")

        # ── Work Updates (last 2 weeks) ─────────────────────────────
        for user in all_users:
            if user.role == "admin":
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
                    "Worked on feature X",
                    "Bug fixes",
                    "Code review",
                    "Client meeting",
                    "Documentation update",
                    "Database optimization",
                    "UI improvements",
                    "API integration",
                    "Testing & QA",
                    "Sprint planning",
                    "Team standup",
                    "Research & learning",
                    "Performance review preparation",
                    "Onboarding new team member",
                ]
                tags_pool = [
                    ["frontend", "react"],
                    ["backend", "api"],
                    ["bugfix"],
                    ["meeting", "client"],
                    ["docs"],
                    ["database"],
                    ["ui", "ux"],
                    ["integration"],
                    ["testing"],
                    ["planning"],
                    ["standup"],
                    ["research"],
                    ["performance"],
                    ["onboarding"],
                ]
                descriptions = [
                    "Spent the day on {}. [Dummy data for testing]",
                    "Worked extensively on {}. Made significant progress. [Dummy data]",
                    "Collaborated with the team on {}. Tasks completed successfully. [Dummy]",
                    "Focused on {} and resolved several issues. [Dummy data for testing]",
                ]
                random_dept = random.choice(list(depts.keys()))
                idx = random.randrange(len(titles))
                db.add(
                    WorkUpdate(
                        user_id=user.id,
                        title=titles[idx],
                        description=random.choice(descriptions).format(
                            titles[idx].lower()
                        ),
                        date=d,
                        department=random_dept,
                        tags=tags_pool[idx],
                        created_at=datetime(
                            d.year, d.month, d.day, 17, 0, 0, tzinfo=timezone.utc
                        ),
                    )
                )
        await db.flush()
        print("Work updates seeded.")

        # ── Leave Requests ──────────────────────────────────────────
        alice = existing_users.get("hr")
        mike = existing_users.get("manager")

        for user in all_users:
            if user.role not in ("employee",):
                continue
            if random.random() > 0.6:
                continue

            lt = random.choice([v for k, v in leave_types.items() if k != "unpaid"])
            from_d = today + timedelta(days=random.randint(5, 20))
            to_d = from_d + timedelta(days=random.randint(0, 2))
            status = random.choice(["pending", "approved", "rejected", "cancelled"])
            approver = None
            rejection_reason = None
            if status == "approved":
                approver = alice.id if random.random() > 0.5 else mike.id
            elif status == "rejected":
                approver = mike.id
                rejection_reason = random.choice(
                    [
                        "Needs more detail",
                        "Team has limited coverage that week",
                        "Please reschedule after project deadline",
                        "Insufficient leave balance",
                    ]
                )

            res = await db.execute(
                select(LeaveRequest).where(
                    LeaveRequest.applicant_id == user.id,
                    LeaveRequest.from_date == from_d,
                )
            )
            if res.scalar_one_or_none():
                continue

            leave_reasons = [
                f"[Seed] {lt.name} leave request for testing",
                f"Planning a short break to recharge. Leave type: {lt.name}. [Seed]",
                f"Personal matters to attend to. Using {lt.name} leave. [Seed]",
                f"Medical appointment scheduled. {lt.name} leave. [Seed]",
            ]

            db.add(
                LeaveRequest(
                    applicant_id=user.id,
                    approver_id=approver,
                    leave_type_id=lt.id,
                    from_date=from_d,
                    to_date=to_d,
                    business_days=(to_d - from_d).days + 1,
                    reason=random.choice(leave_reasons),
                    status=status,
                    rejection_reason=rejection_reason,
                    created_at=datetime(
                        today.year,
                        today.month,
                        today.day,
                        10,
                        0,
                        0,
                        tzinfo=timezone.utc,
                    ),
                    updated_at=datetime(
                        today.year,
                        today.month,
                        today.day,
                        14,
                        0,
                        0,
                        tzinfo=timezone.utc,
                    ),
                )
            )
        await db.flush()
        print("Leave requests seeded.")

        # ── Company Roles ────────────────────────────────────────────
        admin_user = existing_users.get("admin")
        sample_roles = [
            {
                "title": "Frontend Developer",
                "desc": "Builds UI components with React/Vue",
                "resp": "Develop and maintain frontend applications, ensure responsive design, collaborate with UX team",
                "skills": ["JavaScript", "React", "CSS", "TypeScript", "Tailwind"],
            },
            {
                "title": "Backend Developer",
                "desc": "Designs APIs and database schemas",
                "resp": "Build scalable backend services, write unit tests, review peer code",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
            },
            {
                "title": "DevOps Engineer",
                "desc": "Manages CI/CD pipelines and cloud infrastructure",
                "resp": "Maintain deployment pipelines, monitor production systems, manage cloud costs",
                "skills": ["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD"],
            },
        ]
        for i, r in enumerate(sample_roles):
            res = await db.execute(
                select(CompanyRole).where(CompanyRole.title == r["title"])
            )
            if not res.scalar_one_or_none():
                db.add(
                    CompanyRole(
                        title=r["title"],
                        description=r["desc"],
                        responsibilities=r["resp"],
                        required_skills=r["skills"],
                        created_by=admin_user.id,
                        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
                        + timedelta(hours=i),
                        updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
                        + timedelta(hours=i + 1),
                    )
                )
        print("Company roles seeded.")

        # ── Company Rules ────────────────────────────────────────────
        sample_rules = [
            {
                "title": "Work from Home Policy",
                "content": "Employees may work from home up to 2 days per week with manager approval. All WFH days must be recorded in the attendance system.",
                "category": "policy",
            },
            {
                "title": "Code of Conduct",
                "content": "All employees must follow the company code of conduct, respecting diversity and maintaining professionalism at all times.",
                "category": "conduct",
            },
            {
                "title": "Leave Application Procedure",
                "content": "All leave requests must be submitted at least 3 business days in advance. Emergency leaves may be accepted with manager discretion.",
                "category": "policy",
            },
        ]
        for i, r in enumerate(sample_rules):
            res = await db.execute(
                select(CompanyRule).where(CompanyRule.title == r["title"])
            )
            if not res.scalar_one_or_none():
                db.add(
                    CompanyRule(
                        title=r["title"],
                        content=r["content"],
                        category=r["category"],
                        created_by=admin_user.id,
                        is_active=True,
                        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
                        + timedelta(hours=i),
                        updated_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
                        + timedelta(hours=i + 1),
                    )
                )
        print("Company rules seeded.")

        # ── Chat Sessions & Messages ─────────────────────────────────
        user_chat_messages = {
            "employee": [
                ("user", "What is the WFH policy?"),
                (
                    "assistant",
                    "Employees may work from home up to 2 days per week with manager approval. All WFH days must be recorded in the attendance system.",
                ),
                ("user", "How do I apply for leave?"),
                (
                    "assistant",
                    "You can apply for leave through the Leave section. Requests should be submitted at least 3 business days in advance.",
                ),
            ],
            "hr": [
                ("user", "Show me attendance reports for this month"),
                (
                    "assistant",
                    "Here is the attendance summary for this month. All employees have consistent records with minimal absences.",
                ),
                ("user", "How many employees are on leave today?"),
                (
                    "assistant",
                    "There are currently 2 employees on approved leave today.",
                ),
            ],
        }

        chat_created_at = datetime(
            today.year, today.month, today.day, 9, 0, 0, tzinfo=timezone.utc
        )
        for role_key, role_user in existing_users.items():
            if role_key == "admin":
                continue
            messages_list = user_chat_messages.get(
                role_key, user_chat_messages["employee"]
            )
            session_title = (
                "HR Policy Questions"
                if role_key == "employee"
                else "Dashboard Overview"
            )

            cs = ChatSession(
                user_id=role_user.id,
                title=session_title,
                created_at=chat_created_at,
                updated_at=chat_created_at + timedelta(minutes=30),
            )
            db.add(cs)
            await db.flush()

            for j, (msg_role, msg_content) in enumerate(messages_list):
                citations = None
                if msg_role == "assistant" and "policy" in msg_content.lower():
                    citations = [
                        {"source": "Work from Home Policy", "url": "/rules/1"},
                        {"source": "Company Handbook v2.1", "url": "/docs/handbook"},
                    ]
                db.add(
                    ChatMessage(
                        session_id=cs.id,
                        role=msg_role,
                        content=msg_content,
                        citations=citations,
                        created_at=cs.created_at + timedelta(minutes=5 * j),
                    )
                )
        await db.flush()
        print("Chat sessions & messages seeded.")

        # ── Chat Feedback ────────────────────────────────────────────
        feedback_queries = [
            "What is the company leave policy?",
            "How do I reset my password?",
            "Show my attendance for this week",
            "Tell me about company roles",
        ]
        feedback_responses = [
            "The company provides casual, sick, earned, paid, and unpaid leave types. Each has specific allocation and rules.",
            "You can reset your password through the settings page. Click on 'Change Password' and follow the instructions.",
            "Your attendance for this week shows all days as 'present' with regular check-in and check-out times.",
            "Company roles define job titles, responsibilities, and required skills. Check the Roles section for details.",
        ]
        feedback_texts = [None, "Very helpful, thanks!", "Could be more detailed", None]

        for i, feedback_user in enumerate(all_users[:4]):
            session_id_str = f"session_{feedback_user.id.hex[:8]}"
            db.add(
                ChatFeedback(
                    user_id=feedback_user.id,
                    session_id=session_id_str,
                    query=feedback_queries[i],
                    response=feedback_responses[i],
                    rating=random.choice([True, True, False]),
                    feedback_text=random.choice(feedback_texts),
                    created_at=datetime(
                        today.year,
                        today.month,
                        today.day,
                        11,
                        0,
                        0,
                        tzinfo=timezone.utc,
                    )
                    + timedelta(hours=i),
                )
            )
        await db.flush()
        print("Chat feedback seeded.")

        # ── Commit ──────────────────────────────────────────────────
        await db.commit()
        print("\nAll dummy data seeded successfully!")
        print("Users & passwords:")
        for ud in users_data:
            print(f"  {ud['email']} / 12345678")


if __name__ == "__main__":
    asyncio.run(main())
