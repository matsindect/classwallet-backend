"""FastAPI router for fee management endpoints.

Exposes endpoints for fee structure CRUD, publishing a fee structure,
generating invoices from a published structure, and listing invoices.
All endpoints require authentication and appropriate permissions.

All responses are wrapped in the uniform ``success_response`` envelope.
"""

from fastapi import APIRouter, Depends, Query

from app.core.di import get_fee_service
from app.core.policy import enforce
from app.core.response import success_response
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.fees.schemas import FeeStructureCreate, FeeStructureUpdate
from app.modules.fees.service import FeeService

router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("/structures")
async def list_structures(
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """List all fee structures for the current user's school.

    Requires the ``fees.read`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A success envelope containing a list of fee structures.
    """
    enforce(current_user, "fees.read")
    structures = await service.list_structures(current_user.school_id)
    return success_response(data=structures)


@router.post("/structures", status_code=201)
async def create_structure(
    body: FeeStructureCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Create a new fee structure for the current user's school.

    Requires the ``fees.create`` permission.

    Args:
        body: Fee structure creation payload.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A success envelope containing the created fee structure.
    """
    enforce(current_user, "fees.create")
    data = body.model_dump(exclude_unset=True, by_alias=False)
    structure = await service.create_structure(
        school_id=current_user.school_id,
        data=data,
        actor_id=current_user.id,
    )
    return success_response(data=structure)


@router.patch("/structures/{structure_id}")
async def update_structure(
    structure_id: str,
    body: FeeStructureUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Partially update an existing fee structure.

    Only DRAFT structures can be updated. Requires the ``fees.update``
    permission.

    Args:
        structure_id: UUID of the fee structure to update.
        body: Fields to update (only set fields are applied).
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A success envelope containing the updated fee structure.

    Raises:
        NotFoundError: If the fee structure does not exist.
        ConflictError: If the fee structure is already published.
    """
    enforce(current_user, "fees.update")
    data = body.model_dump(exclude_unset=True, by_alias=False)
    structure = await service.update_structure(
        structure_id=structure_id,
        data=data,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return success_response(data=structure)


@router.post("/structures/{structure_id}/publish")
async def publish_structure(
    structure_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Publish a fee structure, making it available for invoice generation.

    Requires the ``fees.publish`` permission.

    Args:
        structure_id: UUID of the fee structure to publish.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A success envelope containing the published fee structure.

    Raises:
        NotFoundError: If the fee structure does not exist.
        ConflictError: If already published.
    """
    enforce(current_user, "fees.publish")
    structure = await service.publish_structure(
        structure_id=structure_id,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return success_response(data=structure)


@router.post("/structures/{structure_id}/generate-invoices")
async def generate_invoices(
    structure_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Generate invoices for all eligible students from a fee structure.

    The fee structure must be published. Students are selected based on the
    grades defined in the fee structure. Requires the ``invoices.create``
    permission.

    Args:
        structure_id: UUID of the published fee structure.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A success envelope containing ``{"count": N}``.

    Raises:
        NotFoundError: If the fee structure does not exist.
        ValidationError: If the fee structure is not published.
    """
    enforce(current_user, "invoices.create")
    count = await service.generate_invoices(
        structure_id=structure_id,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return success_response(data={"count": count})


# TODO: The API contract specifies GET /invoices as a top-level route.
# For now, invoices are served under /fees/invoices. A separate router
# or main.py registration may be needed to serve GET /invoices directly.
@router.get("/invoices")
async def list_invoices(
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
    studentId: str | None = Query(None),  # noqa: N803
):
    """List invoices, optionally filtered by student.

    Requires the ``invoices.read`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).
        studentId: Optional student UUID to filter invoices.

    Returns:
        A success envelope containing a list of invoice objects.
    """
    enforce(current_user, "invoices.read")
    invoices = await service.list_invoices(current_user.school_id, studentId)
    return success_response(data=invoices)
