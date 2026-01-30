from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) == 'super_admin')


class IsSchoolAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) in ['admin', 'super_admin'])


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) == 'teacher')


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) == 'student')


class IsSchoolMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) in ['admin', 'teacher', 'student', 'super_admin'])


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'role', None) in ['teacher', 'admin', 'super_admin'])


class IsOwnerOrSchoolAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'role', None) == 'super_admin':
            return True
        # Owner
        try:
            if getattr(obj, 'created_by', None) == user:
                return True
        except Exception:
            pass
        # School admin for same school
        try:
            if getattr(user, 'role', None) == 'admin' and getattr(obj, 'school', None) == getattr(user, 'school', None):
                return True
        except Exception:
            pass
        return False


class IsStudentOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'role', None) == 'super_admin':
            return True
        # If object has student attribute
        try:
            return getattr(obj, 'student', None) == user
        except Exception:
            return False
