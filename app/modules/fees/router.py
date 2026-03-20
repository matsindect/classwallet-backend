"""FastAPI router for fee management endpoints.

Exposes endpoints for fee structure CRUD, publishing a fee structure,
generating invoices from a published structure, and listing invoices.
All endpoints require authentication and the ``manage_fees`` permission.
"""

from fastapi import APIRouter, Depends, Query

from app.core.di import get_fee_service
from app.core.policy import enforce
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.fees.schemas import (
    FeeStructureCreate,
    FeeStructureResponse,
    FeeStructureUpdate,
    InvoiceGenerationResponse,
    StudentInvoiceResponse,
)
from app.modules.fees.service import FeeService

router = APIRouter(prefix="/fees", tags=["Fees"])


@router.get("/structures", response_model=list[FeeStructureResponse])
async def list_structures(
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """List all fee structures for the current user's school.

    Requires the ``manage_fees`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        A list of ``FeeStructureResponse`` objects.
    """
    enforce(current_user.role, "manage_fees")
    structures = await service.list_structures(current_user.school_id)
    return [FeeStructureResponse.model_validate(s) for s in structures]


@router.post("/structures", response_model=FeeStructureResponse, status_code=201)
async def create_structure(
    body: FeeStructureCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Create a new fee structure for the current user's school.

    Requires the ``manage_fees`` permission.

    Args:
        body: Fee structure creation payload.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        The created fee structure as a ``FeeStructureResponse``.
    """
    enforce(current_user.role, "manage_fees")
    structure = await service.create_structure(
        school_id=current_user.school_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return FeeStructureResponse.model_validate(structure)


@router.patch("/structures/{structure_id}", response_model=FeeStructureResponse)
async def update_structure(
    structure_id: str,
    body: FeeStructureUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Partially update an existing fee structure.

    Requires the ``manage_fees`` permission.

    Args:
        structure_id: UUID of the fee structure to update.
        body: Fields to update (only set fields are applied).
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        The updated fee structure as a ``FeeStructureResponse``.

    Raises:
        NotFoundError: If the fee structure does not exist.
    """
    enforce(current_user.role, "manage_fees")
    structure = await service.update_structure(
        structure_id=structure_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return FeeStructureResponse.model_validate(structure)


@router.post("/structures/{structure_id}/publish", response_model=FeeStructureResponse)
async def publish_structure(
    structure_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Publish a fee structure, making it available for invoice generation.

    Requires the ``manage_fees`` permission.

    Args:
        structure_id: UUID of the fee structure to publish.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        The published fee structure as a ``FeeStructureResponse``.

    Raises:
        NotFoundError: If the fee structure does not exist.
    """
    enforce(current_user.role, "manage_fees")
    structure = await service.publish_structure(
        structure_id=structure_id,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return FeeStructureResponse.model_validate(structure)


@router.post("/structures/{structure_id}/invoices", response_model=InvoiceGenerationResponse)
async def generate_invoices(
    structure_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
):
    """Generate invoices for all eligible students from a fee structure.

    The fee structure must be published. If it targets a specific grade,
    only students in that grade are invoiced; otherwise all students in
    the school receive an invoice. Requires the ``manage_fees`` permission.

    Args:
        structure_id: UUID of the published fee structure.
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).

    Returns:
        An ``InvoiceGenerationResponse`` with the count of created invoices.

    Raises:
        NotFoundError: If the fee structure does not exist.
        ValidationError: If the fee structure is not published.
    """
    enforce(current_user.role, "manage_fees")
    count = await service.generate_invoices(
        structure_id=structure_id,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return InvoiceGenerationResponse(count=count)


@router.get("/invoices", response_model=list[StudentInvoiceResponse])
async def list_invoices(
    current_user: UserResponse = Depends(get_current_user),
    service: FeeService = Depends(get_fee_service),
    studentId: str | None = Query(None),  # noqa: N803
):
    """List invoices, optionally filtered by student.

    Requires the ``manage_fees`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: FeeService instance (injected).
        studentId: Optional student UUID to filter invoices.

    Returns:
        A list of ``StudentInvoiceResponse`` objects.
    """
    enforce(current_user.role, "manage_fees")
    invoices = await service.list_invoices(current_user.school_id, studentId)
    return [StudentInvoiceResponse.model_validate(i) for i in invoices]
