"""
Permission classes for role-based access control and API endpoints.
"""

from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Allows access only to super admin users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'super_admin'


class IsSchoolAdmin(BasePermission):
    """
    Allows access to school admins and super admins.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'super_admin':
            return True
        return request.user.role == 'admin' and request.user.school is not None


class IsTeacher(BasePermission):
    """
    Allows access to teachers and higher roles (admin, super_admin).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in ['super_admin', 'admin', 'teacher']


class IsStudent(BasePermission):
    """
    Allows access to students and higher roles.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in ['super_admin', 'admin', 'teacher', 'student']


class IsSchoolMember(BasePermission):
    """
    Allows access to users belonging to the same school (via middleware).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'super_admin':
            return True
        return request.user.school == getattr(request, 'school', None)


class IsOwnerOrSchoolAdmin(BasePermission):
    """
    Allows access to object owners or school admins/super admins.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'super_admin':
            return True
        if hasattr(obj, 'school'):
            return obj.school == request.user.school and (
                request.user.role == 'admin' or
                getattr(obj, 'user', None) == request.user or
                getattr(obj, 'student', None) == request.user
            )
        return False


class IsStudentOwner(BasePermission):
    """
    Allows students to access only their own data.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'student':
            return getattr(obj, 'student', None) == request.user or getattr(obj, 'user', None) == request.user
        return True  # Allow other roles to pass through to other permission checks


class IsTeacherOrAdmin(BasePermission):
    """
    Allows access to teachers and admins for school-specific operations.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'super_admin':
            return True
        return request.user.role in ['admin', 'teacher'] and request.user.school is not None

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'super_admin':
            return True
        if hasattr(obj, 'school'):
            return obj.school == request.user.school
        return False
