from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .models import School, User, ClassSection, Subject, Grade, Attendance, StudentEnrollment, GradingPeriod
from authentication.permissions import IsSchoolAdmin, IsTeacher, IsStudent, IsSuperAdmin
from django.contrib.auth.decorators import user_passes_test

def is_school_admin_or_teacher(user):
    """Check if user is school admin or teacher"""
    return user.role in ['admin', 'teacher', 'super_admin']

def is_school_member(user):
    """Check if user is any school member"""
    return user.role in ['admin', 'teacher', 'student', 'super_admin']

@login_required
@user_passes_test(is_school_admin_or_teacher)
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    school = request.school
    
    # Get date range for analysis
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=90)  # Last 3 months
    
    context = {
        'school': school,
        'title': 'Analytics Dashboard',
        'date_range': {
            'start': start_date,
            'end': end_date
        }
    }
    
    # Get basic stats
    context.update(get_basic_stats(school))
    
    # Get grade analytics
    context.update(get_grade_analytics(school, start_date, end_date))
    
    # Get attendance analytics
    context.update(get_attendance_analytics(school, start_date, end_date))
    
    # Get performance analytics
    context.update(get_performance_analytics(school))
    
    return render(request, 'analytics/dashboard.html', context)

@login_required
@user_passes_test(is_school_member)
def student_analytics(request, student_id):
    """Individual student analytics view"""
    student = get_object_or_404(User, id=student_id, role='student')
    
    # Check permissions
    if request.user.role == 'student' and request.user.id != student.id:
        return render(request, '403.html', {'error': 'Access denied'}, status=403)
    elif request.user.role in ['admin', 'teacher'] and student.school != request.user.school:
        return render(request, '403.html', {'error': 'Access denied'}, status=403)
    
    context = {
        'student': student,
        'title': f'{student.get_full_name()} Analytics'
    }
    
    # Get student-specific analytics
    context.update(get_student_analytics(student))
    
    return render(request, 'analytics/student_analytics.html', context)

@login_required
@user_passes_test(is_school_admin_or_teacher)
def class_analytics(request, class_id):
    """Class section analytics view"""
    class_section = get_object_or_404(ClassSection, id=class_id)
    
    # Check permissions
    if request.user.role == 'admin' and class_section.school != request.user.school:
        return render(request, '403.html', {'error': 'Access denied'}, status=403)
    elif request.user.role == 'teacher' and class_section.teacher != request.user:
        return render(request, '403.html', {'error': 'Access denied'}, status=403)
    
    context = {
        'class_section': class_section,
        'title': f'{class_section.name} Analytics'
    }
    
    # Get class-specific analytics
    context.update(get_class_analytics(class_section))
    
    return render(request, 'analytics/class_analytics.html', context)

# API Views for Analytics Data

@login_required
@user_passes_test(is_school_admin_or_teacher)
def grade_distribution_api(request):
    """API endpoint for grade distribution data"""
    school = request.school
    subject_id = request.GET.get('subject_id')
    grading_period_id = request.GET.get('grading_period_id')
    
    # Build queryset
    grades = Grade.objects.filter(school=school)
    
    if subject_id:
        grades = grades.filter(subject_id=subject_id)
    if grading_period_id:
        grades = grades.filter(grading_period_id=grading_period_id)
    
    # Get grade distribution
    distribution = grades.values('letter_grade').annotate(
        count=Count('id'),
        percentage=Count('id') * 100.0 / grades.count()
    ).order_by('letter_grade')
    
    return JsonResponse({
        'distribution': list(distribution),
        'total_students': grades.values('student').distinct().count(),
        'average_score': grades.aggregate(avg_score=Avg('score'))['avg_score'] or 0
    })

@login_required
@user_passes_test(is_school_admin_or_teacher)
def attendance_trends_api(request):
    """API endpoint for attendance trends data"""
    school = request.school
    class_id = request.GET.get('class_id')
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Build queryset
    attendance = Attendance.objects.filter(
        school=school,
        date__range=[start_date, end_date]
    )
    
    if class_id:
        attendance = attendance.filter(class_section_id=class_id)
    
    # Get daily attendance trends
    daily_stats = attendance.values('date').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late')),
        excused=Count('id', filter=Q(status='excused'))
    ).order_by('date')
    
    # Calculate percentages
    for stat in daily_stats:
        if stat['total'] > 0:
            stat['present_percentage'] = (stat['present'] / stat['total']) * 100
            stat['absent_percentage'] = (stat['absent'] / stat['total']) * 100
            stat['late_percentage'] = (stat['late'] / stat['total']) * 100
            stat['excused_percentage'] = (stat['excused'] / stat['total']) * 100
        else:
            stat['present_percentage'] = 0
            stat['absent_percentage'] = 0
            stat['late_percentage'] = 0
            stat['excused_percentage'] = 0
    
    return JsonResponse({
        'trends': list(daily_stats),
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    })

@login_required
@user_passes_test(is_school_admin_or_teacher)
def performance_comparison_api(request):
    """API endpoint for performance comparison data"""
    school = request.school
    grading_period_id = request.GET.get('grading_period_id')
    
    # Get subjects and their average scores
    subjects_data = []
    subjects = Subject.objects.filter(school=school)
    
    for subject in subjects:
        grades = Grade.objects.filter(
            subject=subject,
            school=school
        )
        
        if grading_period_id:
            grades = grades.filter(grading_period_id=grading_period_id)
        
        avg_score = grades.aggregate(avg=Avg('score'))['avg'] or 0
        student_count = grades.values('student').distinct().count()
        
        subjects_data.append({
            'subject_name': subject.name,
            'subject_code': subject.code,
            'average_score': round(avg_score, 2),
            'student_count': student_count,
            'grade_distribution': get_subject_grade_distribution(grades)
        })
    
    return JsonResponse({
        'subjects': subjects_data,
        'grading_period_id': grading_period_id
    })

@login_required
@user_passes_test(is_school_admin_or_teacher)
def student_performance_api(request, student_id):
    """API endpoint for individual student performance data"""
    student = get_object_or_404(User, id=student_id, role='student', school=request.school)
    
    # Get student's grades
    grades = Grade.objects.filter(
        student=student,
        school=request.school
    ).select_related('subject', 'grading_period').order_by('grading_period__start_date', 'subject__name')
    
    # Performance over time
    performance_data = []
    for grade in grades:
        performance_data.append({
            'date': grade.grading_period.start_date.isoformat(),
            'subject': grade.subject.name,
            'score': grade.score,
            'letter_grade': grade.letter_grade,
            'grading_period': grade.grading_period.name
        })
    
    # Subject-wise performance
    subject_performance = grades.values('subject__name').annotate(
        avg_score=Avg('score'),
        count=Count('id')
    )
    
    # Attendance summary
    attendance_stats = Attendance.objects.filter(
        student=student,
        school=request.school
    ).values('status').annotate(count=Count('id'))
    
    return JsonResponse({
        'student': {
            'id': student.id,
            'name': student.get_full_name(),
            'username': student.username
        },
        'performance_over_time': performance_data,
        'subject_performance': list(subject_performance),
        'attendance_stats': list(attendance_stats),
        'overall_average': grades.aggregate(avg=Avg('score'))['avg'] or 0
    })

# Helper Functions

def get_basic_stats(school):
    """Get basic school statistics"""
    total_students = User.objects.filter(school=school, role='student').count()
    total_teachers = User.objects.filter(school=school, role='teacher').count()
    total_classes = ClassSection.objects.filter(school=school).count()
    total_subjects = Subject.objects.filter(school=school).count()
    
    # Active users (logged in within last 30 days)
    active_students = User.objects.filter(
        school=school,
        role='student',
        last_login__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    return {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_classes': total_classes,
        'total_subjects': total_subjects,
        'active_students': active_students
    }

def get_grade_analytics(school, start_date, end_date):
    """Get grade analytics for the school"""
    # Average scores by subject
    subject_averages = Grade.objects.filter(
        school=school,
        created_at__date__range=[start_date, end_date]
    ).values('subject__name').annotate(
        avg_score=Avg('score'),
        student_count=Count('student', distinct=True)
    ).order_by('-avg_score')
    
    # Grade distribution
    grade_distribution = Grade.objects.filter(
        school=school,
        created_at__date__range=[start_date, end_date]
    ).values('letter_grade').annotate(
        count=Count('id')
    ).order_by('letter_grade')
    
    # Overall school average
    overall_average = Grade.objects.filter(
        school=school,
        created_at__date__range=[start_date, end_date]
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    return {
        'subject_averages': list(subject_averages),
        'grade_distribution': list(grade_distribution),
        'overall_average': round(overall_average, 2)
    }

def get_attendance_analytics(school, start_date, end_date):
    """Get attendance analytics for the school"""
    # Daily attendance trends
    daily_attendance = Attendance.objects.filter(
        school=school,
        date__range=[start_date, end_date]
    ).values('date').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late'))
    ).order_by('date')
    
    # Attendance by class
    class_attendance = Attendance.objects.filter(
        school=school,
        date__range=[start_date, end_date]
    ).values('class_section__name').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')),
        late=Count('id', filter=Q(status='late'))
    ).order_by('class_section__name')
    
    # Overall attendance rate
    total_attendance = Attendance.objects.filter(
        school=school,
        date__range=[start_date, end_date]
    ).count()
    
    present_attendance = Attendance.objects.filter(
        school=school,
        date__range=[start_date, end_date],
        status='present'
    ).count()
    
    attendance_rate = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0
    
    return {
        'daily_attendance': list(daily_attendance),
        'class_attendance': list(class_attendance),
        'attendance_rate': round(attendance_rate, 2)
    }

def get_performance_analytics(school):
    """Get performance analytics for the school"""
    # Top performing students
    top_students = Grade.objects.filter(school=school).values(
        'student__id',
        'student__username',
        'student__first_name',
        'student__last_name'
    ).annotate(
        avg_score=Avg('score'),
        grade_count=Count('id')
    ).filter(
        grade_count__gte=3  # Students with at least 3 grades
    ).order_by('-avg_score')[:10]
    
    # Subject performance
    subject_performance = Subject.objects.filter(school=school).annotate(
        avg_score=Avg('grades__score'),
        student_count=Count('grades__student', distinct=True)
    ).order_by('-avg_score')
    
    return {
        'top_students': list(top_students),
        'subject_performance': list(subject_performance)
    }

def get_student_analytics(student):
    """Get analytics for a specific student"""
    # Overall performance
    overall_avg = Grade.objects.filter(student=student).aggregate(avg=Avg('score'))['avg'] or 0
    
    # Subject-wise performance
    subject_performance = Grade.objects.filter(student=student).values(
        'subject__name'
    ).annotate(
        avg_score=Avg('score'),
        count=Count('id')
    ).order_by('-avg_score')
    
    # Performance over time
    performance_over_time = Grade.objects.filter(student=student).values(
        'grading_period__name',
        'grading_period__start_date'
    ).annotate(
        avg_score=Avg('score')
    ).order_by('grading_period__start_date')
    
    # Attendance record
    attendance_record = Attendance.objects.filter(student=student).values('status').annotate(
        count=Count('id')
    )
    
    return {
        'overall_average': round(overall_avg, 2),
        'subject_performance': list(subject_performance),
        'performance_over_time': list(performance_over_time),
        'attendance_record': list(attendance_record)
    }

def get_class_analytics(class_section):
    """Get analytics for a specific class section"""
    # Class performance
    class_avg = Grade.objects.filter(
        student__enrollments__class_section=class_section
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    # Student performance in class
    student_performance = Grade.objects.filter(
        student__enrollments__class_section=class_section
    ).values(
        'student__id',
        'student__username',
        'student__first_name',
        'student__last_name'
    ).annotate(
        avg_score=Avg('score'),
        grade_count=Count('id')
    ).order_by('-avg_score')
    
    # Subject-wise performance for class
    subject_performance = Grade.objects.filter(
        student__enrollments__class_section=class_section
    ).values('subject__name').annotate(
        avg_score=Avg('score'),
        student_count=Count('student', distinct=True)
    ).order_by('-avg_score')
    
    # Attendance for class
    attendance_stats = Attendance.objects.filter(class_section=class_section).values('status').annotate(
        count=Count('id')
    )
    
    return {
        'class_average': round(class_avg, 2),
        'student_performance': list(student_performance),
        'subject_performance': list(subject_performance),
        'attendance_stats': list(attendance_stats)
    }

def get_subject_grade_distribution(grades):
    """Get grade distribution for a subject"""
    distribution = grades.values('letter_grade').annotate(
        count=Count('id')
    ).order_by('letter_grade')
    return list(distribution)