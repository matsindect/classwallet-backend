"""HTTP client for the ZB Bank external API.

Wraps the three ZB Bank endpoints (all-payments, pick-all-pending,
student-details) using httpx with async support. Handles authentication
via institutionId/password in the request body and provides structured
error handling for network and API failures.
"""

import httpx

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ZBBankAPIError(AppError):
    """Raised when the ZB Bank API returns an error response."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(code="ZB_BANK_ERROR", message=message, status_code=status_code)


class ZBBankClient:
    """Async HTTP client for interacting with ZB Bank APIs.

    Uses httpx to call the ZB Bank payment and student-details endpoints.
    Credentials are loaded from application settings.

    Attributes:
        base_url: The ZB Bank API base URL.
        institution_id: The institution ID for authentication.
        password: The institution password for authentication.
        biller_id: The biller ID for student uploads.
        timeout: Request timeout in seconds.
    """

    def __init__(self):
        self.base_url = settings.ZB_BANK_BASE_URL.rstrip("/")
        self.institution_id = settings.ZB_BANK_INSTITUTION_ID
        self.password = settings.ZB_BANK_PASSWORD
        self.biller_id = settings.ZB_BANK_BILLER_ID
        self.timeout = settings.ZB_BANK_TIMEOUT_SECONDS

    def _auth_payload(self) -> dict:
        """Return the authentication body fields shared by payment endpoints.

        Returns:
            A dict with institutionId and password.
        """
        return {
            "institutionId": self.institution_id,
            "password": self.password,
        }

    async def fetch_all_payments(self) -> list[dict]:
        """Fetch all payment transactions from ZB Bank.

        Calls ``POST /alerts/payments/all-payments``.

        Returns:
            A list of transaction dicts from the ZB Bank response.

        Raises:
            ZBBankAPIError: If the API request fails or returns a non-200 status.
        """
        url = f"{self.base_url}/alerts/payments/all-payments"
        return await self._post_payments(url)

    async def fetch_pending_payments(self) -> list[dict]:
        """Fetch only pending (unpicked) payment transactions from ZB Bank.

        Calls ``POST /alerts/payments/pick-all-pending``.

        Returns:
            A list of pending transaction dicts from the ZB Bank response.

        Raises:
            ZBBankAPIError: If the API request fails or returns a non-200 status.
        """
        url = f"{self.base_url}/alerts/payments/pick-all-pending"
        return await self._post_payments(url)

    async def upload_student_details(
        self,
        customer_account: str,
        customer_name: str,
        level: str = "",
        program: str = "",
    ) -> dict:
        """Upload student details to ZB Bank for bill-pay registration.

        Calls ``POST /api/billpay/student-details``.

        Args:
            customer_account: The student registration/account number.
            customer_name: Full name of the student.
            level: Optional student level/grade.
            program: Optional degree/program name.

        Returns:
            The parsed JSON response from ZB Bank.

        Raises:
            ZBBankAPIError: If the API request fails or returns an error.
        """
        url = f"{self.base_url}/api/billpay/student-details"
        payload = {
            "billerId": self.biller_id,
            "customerAccount": customer_account,
            "customerAccountDetails1": level,
            "customerAccountDetails2": program,
            "customerName": customer_name,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

            if response.status_code in (200, 201):
                return response.json()

            logger.error(
                "zb_bank_student_upload_failed",
                status=response.status_code,
                body=response.text[:500],
            )
            raise ZBBankAPIError(
                message=f"ZB Bank student upload failed with status {response.status_code}",
                status_code=502,
            )

        except httpx.RequestError as exc:
            logger.error("zb_bank_student_upload_network_error", error=str(exc))
            raise ZBBankAPIError(message=f"Failed to connect to ZB Bank: {exc}") from exc

    async def _post_payments(self, url: str) -> list[dict]:
        """Send a POST request to a ZB Bank payments endpoint.

        Args:
            url: The full URL to call.

        Returns:
            A list of transaction dicts from the response.

        Raises:
            ZBBankAPIError: On HTTP errors or network failures.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=self._auth_payload())

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                return data if isinstance(data, list) else []

            logger.error(
                "zb_bank_payments_fetch_failed",
                url=url,
                status=response.status_code,
                body=response.text[:500],
            )
            raise ZBBankAPIError(
                message=f"ZB Bank API returned status {response.status_code}",
                status_code=502,
            )

        except httpx.RequestError as exc:
            logger.error("zb_bank_network_error", url=url, error=str(exc))
            raise ZBBankAPIError(message=f"Failed to connect to ZB Bank: {exc}") from exc
