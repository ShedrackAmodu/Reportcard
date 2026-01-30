"""
Reusable mixins for ViewSets and Views to reduce code redundancy.
Consolidates common patterns like school filtering, permission checks, and queryset optimization.
"""
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response


class SchoolFilterMixin:
    """Mixin for filtering queryset by school based on user role"""
    
    def get_school_queryset(self, queryset):
        """Filter queryset by school context"""
        if not hasattr(self.request, 'user'):
            return queryset.none()
        
        if self.request.user.role == 'super_admin':
            return queryset
        
        school = getattr(self.request, 'school', self.request.user.school)
        if school:
            return queryset.filter(school=school)
        
        return queryset.none()


class RoleBasedPermissionMixin:
    """Mixin for role-based queryset filtering"""
    
    def filter_by_role(self, queryset):
        """Filter queryset based on user role"""
        user = self.request.user
        
        if user.role == 'super_admin':
            return queryset
        elif user.role == 'admin':
            return queryset.filter(school=user.school)
        elif user.role == 'teacher':
            return queryset.filter(school=user.school)
        else:
            # Students see only their own data
            return queryset.filter(user_id=user.id) if hasattr(queryset, 'filter') else queryset
        
        return queryset


class StandardViewSet(SchoolFilterMixin, RoleBasedPermissionMixin, viewsets.ModelViewSet):
    """Base ViewSet with common school filtering and permission handling"""
    
    def get_queryset(self):
        queryset = self.queryset
        
        # Apply school filtering for models with school FK
        if hasattr(self.queryset.model, 'school'):
            queryset = self.get_school_queryset(queryset)
        
        # Apply role-based filtering
        queryset = self.filter_by_role(queryset)
        
        return queryset


class StudentOwnerFilterMixin:
    """Mixin for checking if student owns the resource"""
    
    def check_student_owner(self, obj):
        """Check if current user is the student or authorized to view"""
        user = self.request.user
        
        if user.role == 'super_admin':
            return True
        elif user.role == 'admin':
            return obj.school == user.school
        elif user.role == 'student':
            return hasattr(obj, 'student') and obj.student == user
        elif user.role == 'teacher':
            # Teacher can view if student is in their class
            if hasattr(obj, 'student'):
                from apps.models import StudentEnrollment
                return StudentEnrollment.objects.filter(
                    student=obj.student,
                    class_section__teacher=user
                ).exists()
        
        return False


class ExportMixin:
    """Mixin for common export functionality"""
    
    def get_export_queryset(self):
        """Get filtered queryset for export based on permissions"""
        queryset = self.queryset
        user = self.request.user
        
        if user.role == 'admin':
            return queryset.filter(school=user.school)
        elif user.role == 'teacher':
            # Teachers export only for their students
            from apps.models import StudentEnrollment
            student_ids = StudentEnrollment.objects.filter(
                class_section__teacher=user
            ).values_list('student_id', flat=True)
            
            if hasattr(queryset.model, 'student'):
                return queryset.filter(student_id__in=student_ids, school=user.school)
            
            return queryset.filter(school=user.school)
        elif user.role == 'student':
            if hasattr(queryset.model, 'student'):
                return queryset.filter(student=user)
        elif user.role == 'super_admin':
            return queryset
        
        return queryset.none()
    
    def validate_export_permission(self):
        """Check if user can export"""
        user = self.request.user
        return user.role in ['super_admin', 'admin', 'teacher']


class SearchMixin:
    """Mixin for common search functionality across models"""
    
    @staticmethod
    def get_search_fields():
        """Override in subclass to define searchable fields"""
        return []
    
    def build_search_query(self, search_term):
        """Build Q object for search from configured fields"""
        if not search_term or not self.get_search_fields():
            return Q()
        
        q = Q()
        for field in self.get_search_fields():
            q |= Q(**{f"{field}__icontains": search_term})
        
        return q
