"""Leave management tests.

Tests leave balance queries, leave application (including
insufficient-balance rejection), and the full approve workflow
with balance deduction verification.
"""

from __future__ import annotations

import logging

import pytest
from httpx import AsyncClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_leave_balance(client: AsyncClient, test_users):
    """Test retrieving leave balances."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/leaves/balance", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    balances = response.json()
    assert len(balances) > 0
    # Should have casual leave seeded with 18 days
    casual = next(b for b in balances if b["leave_type_name"] == "casual")
    assert casual["remaining_days"] == 18
    assert casual["used_days"] == 0


@pytest.mark.asyncio
async def test_apply_leave_success(client: AsyncClient, test_users):
    """Test successfully applying for leave."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    # Apply for 3 days of casual leave in future: July 1 to July 3, 2026 (Wednesday to Friday)
    apply_payload = {
        "leave_type": "casual",
        "from_date": "2026-07-01",
        "to_date": "2026-07-03",
        "reason": "Family trip",
    }
    response = await client.post(
        "/api/leaves/apply",
        json=apply_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    leave_data = response.json()
    assert leave_data["status"] == "pending"
    assert leave_data["business_days"] == 3
    assert leave_data["reason"] == "Family trip"


@pytest.mark.asyncio
async def test_apply_leave_insufficient_balance(client: AsyncClient, test_users):
    """Test applying for leave with insufficient balance fails."""
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    # Sick leave has 12 days; try to apply for 20 days (July 1 to July 28, 2026)
    apply_payload = {
        "leave_type": "sick",
        "from_date": "2026-07-01",
        "to_date": "2026-07-28",
        "reason": "Medical recovery",
    }
    response = await client.post(
        "/api/leaves/apply",
        json=apply_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Insufficient leave balance" in response.json()["detail"]


@pytest.mark.asyncio
async def test_approve_leave_workflow(client: AsyncClient, test_users):
    """Test the complete leave application, pending checks, and approval lifecycle."""
    # 1. Employee applies
    emp_login = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "password123"},
    )
    emp_token = emp_login.json()["access_token"]

    apply_payload = {
        "leave_type": "casual",
        "from_date": "2026-07-01",
        "to_date": "2026-07-02",
        "reason": "Personal work",
    }
    apply_res = await client.post(
        "/api/leaves/apply",
        json=apply_payload,
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    leave_id = apply_res.json()["id"]

    # 2. HR logs in and views pending leaves
    hr_login = await client.post(
        "/api/auth/login", json={"email": "hr@test.com", "password": "password123"}
    )
    hr_token = hr_login.json()["access_token"]

    pending_res = await client.get(
        "/api/leaves/pending", headers={"Authorization": f"Bearer {hr_token}"}
    )
    assert pending_res.status_code == 200
    pending_ids = [l["id"] for l in pending_res.json()]
    assert leave_id in pending_ids

    # 3. HR approves the leave
    approve_res = await client.patch(
        f"/api/leaves/{leave_id}/approve",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"

    # 4. Employee's balance is deducted
    balance_res = await client.get(
        "/api/leaves/balance", headers={"Authorization": f"Bearer {emp_token}"}
    )
    balances = balance_res.json()
    casual = next(b for b in balances if b["leave_type_name"] == "casual")
    # 18 - 2 business days (July 1 and July 2) = 16 remaining
    assert casual["remaining_days"] == 16
    assert casual["used_days"] == 2
