"""
Permission classes have been moved to authentication app.
Import from authentication.permissions instead.

Example:
    from authentication.permissions import IsSuperAdmin, IsSchoolAdmin, etc.
"""

# For backward compatibility, import from the new location
from authentication.permissions import (
    IsSuperAdmin,
    IsSchoolAdmin,
    IsTeacher,
    IsStudent,
    IsSchoolMember,
    IsOwnerOrSchoolAdmin,
    IsStudentOwner,
    IsTeacherOrAdmin,
)

__all__ = [
    'IsSuperAdmin',
    'IsSchoolAdmin',
    'IsTeacher',
    'IsStudent',
    'IsSchoolMember',
    'IsOwnerOrSchoolAdmin',
    'IsStudentOwner',
    'IsTeacherOrAdmin',
]
