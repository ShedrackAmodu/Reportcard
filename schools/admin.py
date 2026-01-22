from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    School,
    User,
    ClassSection,
    Subject,
    GradingScale,
    StudentEnrollment,
    GradingPeriod,
    Grade,
    Attendance,
    UserApplication,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'role', 'school', 'is_active')
    list_filter = ('role', 'school', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'school')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'school')}),
    )


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ClassSection)
class ClassSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'teacher', 'school')
    list_filter = ('school', 'grade_level')
    search_fields = ('name', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    ordering = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'school')
    list_filter = ('school',)
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(GradingScale)
class GradingScaleAdmin(admin.ModelAdmin):
    list_display = ('name', 'scale_type', 'school')
    list_filter = ('scale_type', 'school')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_section', 'enrollment_date', 'school')
    list_filter = ('school', 'class_section', 'enrollment_date')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'class_section__name')
    ordering = ('-enrollment_date',)


@admin.register(GradingPeriod)
class GradingPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'start_date', 'end_date')
    list_filter = ('school', 'start_date', 'end_date')
    search_fields = ('name',)
    ordering = ('start_date',)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'grading_period', 'score', 'letter_grade', 'is_override', 'school')
    list_filter = ('school', 'subject', 'grading_period', 'is_override')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'subject__name')
    ordering = ('-updated_at',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'class_section', 'date', 'status', 'school')
    list_filter = ('school', 'class_section', 'date', 'status')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'class_section__name')
    ordering = ('-date',)


@admin.register(UserApplication)
class UserApplicationAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'school', 'status', 'submitted_by', 'created_at')
    list_filter = ('role', 'school', 'status')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    actions = ['approve_applications', 'reject_applications']

    def approve_applications(self, request, queryset):
        for application in queryset.filter(status='pending'):
            application.approve(request.user)
        self.message_user(request, f"Approved {queryset.filter(status='pending').count()} applications.")
    approve_applications.short_description = "Approve selected applications"

    def reject_applications(self, request, queryset):
        for application in queryset.filter(status='pending'):
            application.reject(request.user, "Rejected via admin action")
        self.message_user(request, f"Rejected {queryset.filter(status='pending').count()} applications.")
    reject_applications.short_description = "Reject selected applications"
