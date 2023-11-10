"""
Pydantic config:
https://docs.pydantic.dev/latest/api/config/
"""

from pydantic import ConfigDict

PYDANTIC_CONFIG = ConfigDict(
    validate_assignment = True,
    validate_default = True,
    extra = 'forbid',
)