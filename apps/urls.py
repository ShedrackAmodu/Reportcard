from django.urls import path, include

from rest_framework.routers import DefaultRouter

from .views import (
    SchoolViewSet, UserViewSet, ClassSectionViewSet, SubjectViewSet,
    GradingScaleViewSet, GradingPeriodViewSet, StudentEnrollmentViewSet, GradeViewSet, AttendanceViewSet, sync_view, search_api_view,
    dashboard_view, landing_view, school_switch, offline_view, manifest_view, sw_view,
    apk_download_view,
    school_list, school_create, school_update, school_delete,
    user_list, user_create, user_update, user_delete,
    class_section_list, class_section_create, class_section_update, class_section_delete,
    subject_list, subject_create, subject_update, subject_delete,
    grading_scale_list, grading_scale_create, grading_scale_update, grading_scale_delete,
    enrollment_list, enrollment_create, enrollment_update, enrollment_delete,
    grading_period_list, grading_period_create, grading_period_update, grading_period_delete,
    grade_list, grade_bulk_entry, grade_import, grade_create, grade_update, grade_delete,
    attendance_list, attendance_create, attendance_update, attendance_delete,
    application_list, application_review,
    report_card_pdf, report_card_list, batch_report_card_pdf,
    export_grades_excel, export_attendance_excel, export_users_csv
)
from .views import push_sync_view

router = DefaultRouter()
router.register(r'schools', SchoolViewSet)
router.register(r'users', UserViewSet)
router.register(r'class-sections', ClassSectionViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'grading-scales', GradingScaleViewSet)
router.register(r'grading-periods', GradingPeriodViewSet)
router.register(r'student-enrollments', StudentEnrollmentViewSet)
router.register(r'grades', GradeViewSet)
router.register(r'attendance', AttendanceViewSet)


urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/sync/', sync_view, name='sync'),
    path('api/sync/push/', push_sync_view, name='sync_push'),
    path('api/search/', search_api_view, name='search_api'),

    # PWA files
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js', sw_view, name='sw'),

    # Root landing page
    path('', landing_view, name='landing'),

    # Offline fallback page
    path('offline/', offline_view, name='offline'),

    # Web views
    path('dashboard/', dashboard_view, name='dashboard'),
    path('school-switch/', school_switch, name='school_switch'),

    # School Management (Super Admin)
    path('schools/', school_list, name='school_list'),
    path('schools/create/', school_create, name='school_create'),
    path('schools/<int:pk>/update/', school_update, name='school_update'),
    path('schools/<int:pk>/delete/', school_delete, name='school_delete'),

    # User Management
    path('users/', user_list, name='user_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/<int:pk>/update/', user_update, name='user_update'),
    path('users/<int:pk>/delete/', user_delete, name='user_delete'),

    # Class Section Management
    path('class-sections/', class_section_list, name='class_section_list'),
    path('class-sections/create/', class_section_create, name='class_section_create'),
    path('class-sections/<int:pk>/update/', class_section_update, name='class_section_update'),
    path('class-sections/<int:pk>/delete/', class_section_delete, name='class_section_delete'),

    # Subject Management
    path('subjects/', subject_list, name='subject_list'),
    path('subjects/create/', subject_create, name='subject_create'),
    path('subjects/<int:pk>/update/', subject_update, name='subject_update'),
    path('subjects/<int:pk>/delete/', subject_delete, name='subject_delete'),

    # Grading Scale Management
    path('grading-scales/', grading_scale_list, name='grading_scale_list'),
    path('grading-scales/create/', grading_scale_create, name='grading_scale_create'),
    path('grading-scales/<int:pk>/update/', grading_scale_update, name='grading_scale_update'),
    path('grading-scales/<int:pk>/delete/', grading_scale_delete, name='grading_scale_delete'),

    # Student Enrollment Management
    path('enrollments/', enrollment_list, name='enrollment_list'),
    path('enrollments/create/', enrollment_create, name='enrollment_create'),
    path('enrollments/<int:pk>/update/', enrollment_update, name='enrollment_update'),
    path('enrollments/<int:pk>/delete/', enrollment_delete, name='enrollment_delete'),

    # Grading Period Management
    path('grading-periods/', grading_period_list, name='grading_period_list'),
    path('grading-periods/create/', grading_period_create, name='grading_period_create'),
    path('grading-periods/<int:pk>/update/', grading_period_update, name='grading_period_update'),
    path('grading-periods/<int:pk>/delete/', grading_period_delete, name='grading_period_delete'),

    # Grade Management
    path('grades/', grade_list, name='grade_list'),
    path('grades/bulk-entry/', grade_bulk_entry, name='grade_bulk_entry'),
    path('grades/import/', grade_import, name='grade_import'),
    path('grades/create/', grade_create, name='grade_create'),
    path('grades/<int:pk>/update/', grade_update, name='grade_update'),
    path('grades/<int:pk>/delete/', grade_delete, name='grade_delete'),

    # Attendance Management
    path('attendance/', attendance_list, name='attendance_list'),
    path('attendance/create/', attendance_create, name='attendance_create'),
    path('attendance/<int:pk>/update/', attendance_update, name='attendance_update'),
    path('attendance/<int:pk>/delete/', attendance_delete, name='attendance_delete'),

    # Application Management
    path('applications/', application_list, name='application_list'),
    path('applications/<int:pk>/review/', application_review, name='application_review'),

    # Report Card Management
    path('report-cards/', report_card_list, name='report_card_list'),
    path('report-cards/<int:student_id>/pdf/', report_card_pdf, name='report_card_pdf'),
    path('report-cards/batch-pdf/<int:class_id>/', batch_report_card_pdf, name='batch_report_card_pdf'),


    # Export Views
    path('export/grades/excel/', export_grades_excel, name='export_grades_excel'),
    path('export/attendance/excel/', export_attendance_excel, name='export_attendance_excel'),
    path('export/users/csv/', export_users_csv, name='export_users_csv'),

    # APK Download
    path('download/apk/', apk_download_view, name='apk_download'),
]
