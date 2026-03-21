"""Base Pydantic schema with camelCase serialisation.

All API schemas inherit from ``CamelModel`` so that Python-side snake_case
field names are automatically converted to camelCase in JSON responses.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that serialises field names as camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
