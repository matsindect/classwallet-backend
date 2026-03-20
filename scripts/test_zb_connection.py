"""Test script to verify ZB Bank API connectivity.

Run with: .venv/bin/python scripts/test_zb_connection.py
"""

import asyncio
import sys

import httpx

from app.core.config import settings


async def test_connection():
    """Test connectivity to ZB Bank APIs using configured credentials."""
    print("=" * 60)
    print("ZB Bank Connection Test")
    print("=" * 60)
    print(f"  Base URL:       {settings.ZB_BANK_BASE_URL}")
    print(f"  Institution ID: {settings.ZB_BANK_INSTITUTION_ID}")
    print(f"  Password:       {'*' * len(settings.ZB_BANK_PASSWORD)}")
    print(f"  Biller ID:      {settings.ZB_BANK_BILLER_ID}")
    print(f"  Timeout:        {settings.ZB_BANK_TIMEOUT_SECONDS}s")
    print()

    if not settings.ZB_BANK_INSTITUTION_ID:
        print("[ERROR] ZB_BANK_INSTITUTION_ID is not set. Check your .env file.")
        return False

    base_url = settings.ZB_BANK_BASE_URL.rstrip("/")
    payload = {
        "institutionId": settings.ZB_BANK_INSTITUTION_ID,
        "password": settings.ZB_BANK_PASSWORD,
    }

    # Test 1: Fetch all payments
    print("[1/2] Testing POST /alerts/payments/all-payments ...")
    try:
        async with httpx.AsyncClient(timeout=settings.ZB_BANK_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{base_url}/alerts/payments/all-payments",
                json=payload,
            )
        print(f"      Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            count = len(data) if isinstance(data, list) else "N/A"
            print(f"      Transactions returned: {count}")
            if isinstance(data, list) and data:
                sample = data[0]
                print(f"      Sample keys: {list(sample.keys())}")
                print(f"      Sample: id={sample.get('id')}, "
                      f"amount={sample.get('amount')}, "
                      f"reference={sample.get('reference')}, "
                      f"status={sample.get('status')}")
            print("      [OK] All payments endpoint working")
        else:
            print(f"      Response: {resp.text[:300]}")
            print("      [FAIL] Check credentials")
    except httpx.RequestError as e:
        print(f"      [FAIL] Network error: {e}")
        return False

    print()

    # Test 2: Fetch pending payments
    print("[2/2] Testing POST /alerts/payments/pick-all-pending ...")
    try:
        async with httpx.AsyncClient(timeout=settings.ZB_BANK_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{base_url}/alerts/payments/pick-all-pending",
                json=payload,
            )
        print(f"      Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            count = len(data) if isinstance(data, list) else "N/A"
            print(f"      Pending transactions: {count}")
            print("      [OK] Pending payments endpoint working")
        else:
            print(f"      Response: {resp.text[:300]}")
            print("      [FAIL] Check credentials")
    except httpx.RequestError as e:
        print(f"      [FAIL] Network error: {e}")
        return False

    print()
    print("=" * 60)
    print("Connection test complete.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
