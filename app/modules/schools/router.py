"""Platform-level schools management router (SUPER_ADMIN only).

Provides endpoints for listing all schools, onboarding new schools,
and viewing/updating any school by ID. These are platform-wide
operations — not scoped to a single school.
"""

import json

from fastapi import APIRouter, Depends, Query

from app.core.database import async_session_factory
from app.core.errors import NotFoundError
from app.core.pagination import clamp_pagination
from app.core.policy import enforce
from app.core.response import paginated_response, success_response
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.school.models import School
from app.modules.school.repository import SchoolRepository
from app.modules.school.schemas import SchoolCreate, SchoolResponse, SchoolUpdate

router = APIRouter(prefix="/schools", tags=["Schools (Platform)"])


@router.get("")
async def list_schools(
    current_user: UserResponse = Depends(get_current_user),
    search: str | None = Query(None),
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List all schools on the platform (paginated).

    Requires ``schools.read`` permission (SUPER_ADMIN).
    """
    enforce(current_user, "schools.read")

    p, ps = clamp_pagination(page, pageSize)
    offset = (p - 1) * ps

    async with async_session_factory() as session:
        repo = SchoolRepository(session)
        schools, total = await repo.list_schools(offset=offset, limit=ps, search=search)

    data = [SchoolResponse.model_validate(s).model_dump(by_alias=True) for s in schools]
    return paginated_response(data=data, page=p, page_size=ps, total_count=total)


@router.post("", status_code=201)
async def create_school(
    body: SchoolCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    """Onboard a new school to the platform.

    Requires ``schools.create`` permission (SUPER_ADMIN).
    """
    enforce(current_user, "schools.create")

    async with async_session_factory() as session:
        repo = SchoolRepository(session)
        school = School(
            name=body.name,
            address=body.address,
            city=body.city,
            state=body.state,
            country=body.country,
            phone=body.phone,
            email=body.email,
            website=body.website,
            currency=body.currency,
            timezone=body.timezone,
        )
        school = await repo.create_school(school)
        await session.commit()

        data = SchoolResponse.model_validate(school).model_dump(by_alias=True)

    return success_response(data=data)


@router.get("/{school_id}")
async def get_school(
    school_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get a specific school by ID.

    Requires ``schools.read`` permission (SUPER_ADMIN).
    """
    enforce(current_user, "schools.read")

    async with async_session_factory() as session:
        repo = SchoolRepository(session)
        school = await repo.get_school(school_id)

    if not school:
        raise NotFoundError(message="School not found")

    data = SchoolResponse.model_validate(school).model_dump(by_alias=True)
    return success_response(data=data)


@router.patch("/{school_id}")
async def update_school(
    school_id: str,
    body: SchoolUpdate,
    current_user: UserResponse = Depends(get_current_user),
):
    """Update any school by ID.

    Requires ``schools.update`` permission (SUPER_ADMIN).
    """
    enforce(current_user, "schools.update")

    update_data = body.model_dump(exclude_unset=True, by_alias=False)

    # Serialize academic_term_config dict to JSON string for storage
    if "academic_term_config" in update_data and isinstance(
        update_data["academic_term_config"], dict
    ):
        update_data["academic_term_config"] = json.dumps(update_data["academic_term_config"])

    async with async_session_factory() as session:
        repo = SchoolRepository(session)
        school = await repo.update_school(school_id, update_data)
        if not school:
            raise NotFoundError(message="School not found")
        await session.commit()

        data = SchoolResponse.model_validate(school).model_dump(by_alias=True)

    return success_response(data=data)
