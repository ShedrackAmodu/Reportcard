from django.db import IntegrityError, transaction
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.forms import modelformset_factory
from django.db.models import Q, Sum

from apps.students.models import Student
from apps.academics.models import Semester, Subject, Department
from .models import Result, SubjectGroup, Attendance
from .filters import ResultFilter, SubjectGroupFilter
from .forms import (
    TeacherResultForm, TeacherAttendanceForm, 
    TeacherMarkEntryForm, TeacherAttendanceEntryForm,
    ResultFormSet, AttendanceFormSet
)
from permission_handlers.basic import user_is_verified, user_is_teacher
from permission_handlers.administrative import user_is_teacher_or_administrative


@user_passes_test(user_is_verified)
def result_view(request):
    if not request.GET:
        qs = Result.objects.none()
    else:
        qs = Result.objects.all()
    f = ResultFilter(request.GET, queryset=qs)
    ctx = {'filter': f, }
    return render(request, 'result/result_filter.html', ctx)


@user_passes_test(user_is_verified)
def result_detail_view(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk)
    student_results = student.results.select_related('subject', 'semester')
    semesters = list(Semester.objects.all())
    semester_reports = []
    active_semesters = []

    for semester in semesters:
        results = list(student_results.filter(semester=semester))
        if results:
            active_semesters.append(semester)

            subject_count = len(results)
            total_score = sum([(item.total_marks or 0) for item in results])
            avg_score = round(total_score / subject_count, 2) if subject_count else 0
            gpa = round(
                sum([item.grade_point for item in results]) / subject_count, 2
            ) if subject_count else 0

            # Determine class position by semester + department.
            classmates = Student.objects.filter(
                semester=semester,
                admission_student__choosen_department=student.admission_student.choosen_department
            ).annotate(
                semester_total=Sum(
                    'results__total_marks',
                    filter=Q(results__semester=semester)
                )
            ).order_by('-semester_total', 'admission_student__name')
            ranked_ids = [item.pk for item in classmates if item.semester_total is not None]
            try:
                class_position = ranked_ids.index(student.pk) + 1
                class_size = len(ranked_ids)
            except ValueError:
                class_position = None
                class_size = len(ranked_ids)

            semester_reports.append({
                'semester': semester,
                'results': results,
                'summary': {
                'subject_count': subject_count,
                'total_score': total_score,
                'average_score': avg_score,
                'gpa': gpa,
                'class_position': class_position,
                'class_size': class_size,
                }
            })
    ctx = {
        'student': student,
        'semester_reports': semester_reports,
        'active_semesters': active_semesters,
    }
    return render(request, 'result/result_detail.html', ctx)


def find_student(request, student_id):
    """ Find student by given id for result entry."""
    student = Student.objects.filter(temporary_id=student_id).first()
    if not student:
        return JsonResponse({'error': 'Student not found'}, status=404)
    ctx = {
        'student_name': student.admission_student.name,
        'student_batch': student.batch.number,
        'image_url': student.admission_student.photo.url
    }
    return JsonResponse({'data': ctx})


@user_passes_test(user_is_teacher_or_administrative)
def result_entry(request):
    if not request.GET:
        qs = SubjectGroup.objects.none()
    else:
        qs = SubjectGroup.objects.all()

    subject_group_filter = SubjectGroupFilter(
        request.GET,
        queryset=qs
    )

    if request.method == 'POST':
        student_temp_id = request.POST.get('student_id')
        semester_pk = request.POST.get('semester')
        student = Student.objects.filter(temporary_id=student_temp_id).first()
        if not student:
            messages.error(request, 'Invalid student id.')
            return redirect('result:result_entry')
        semester = Semester.objects.filter(pk=semester_pk).first()
        if not semester:
            messages.error(request, 'Please select a valid semester.')
            return redirect('result:result_entry')

        subject_ids = set()
        for key in request.POST.keys():
            if key.startswith('practical_marks.') or key.startswith('theory_marks.'):
                try:
                    subject_ids.add(int(key.split('.')[1]))
                except (IndexError, ValueError):
                    continue

        saved_count = 0
        for subject_id in subject_ids:
            subject = Subject.objects.filter(pk=subject_id).first()
            if not subject:
                continue
            practical_raw = request.POST.get(f'practical_marks.{subject_id}', '').strip()
            theory_raw = request.POST.get(f'theory_marks.{subject_id}', '').strip()
            if practical_raw == '' and theory_raw == '':
                continue
            try:
                practical_marks = int(practical_raw) if practical_raw != '' else None
                theory_marks = int(theory_raw) if theory_raw != '' else None
            except ValueError:
                messages.error(request, f'Invalid marks for {subject}.')
                continue

            if practical_marks is not None and (
                practical_marks < 0 or practical_marks > subject.practical_marks
            ):
                messages.error(
                    request,
                    f'Practical marks for {subject} must be between 0 and {subject.practical_marks}.'
                )
                continue
            if theory_marks is not None and (
                theory_marks < 0 or theory_marks > subject.theory_marks
            ):
                messages.error(
                    request,
                    f'Theory marks for {subject} must be between 0 and {subject.theory_marks}.'
                )
                continue

            Result.objects.update_or_create(
                student=student,
                semester=semester,
                subject=subject,
                defaults={
                    'practical_marks': practical_marks,
                    'theory_marks': theory_marks,
                }
            )
            saved_count += 1
        if saved_count:
            messages.success(request, f'Successfully saved {saved_count} result record(s).')
        return redirect('result:result_entry')
    ctx = {
        'subject_group_filter': subject_group_filter,
    }
    return render(request, 'result/result_entry.html', ctx)


@user_passes_test(user_is_teacher_or_administrative)
def create_subject_group(request):
    departments = Department.objects.all()
    semesters = Semester.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        dept_pk = int(request.POST.get('department'))
        subject_list = request.POST.getlist('subject')
        semester_pk = int(request.POST.get('semester'))

        dept = Department.objects.get(pk=dept_pk)
        semester = Semester.objects.get(pk=semester_pk)

        subject_group = SubjectGroup.objects.create(
            department=dept,
            semester=semester
        )

        subject_objects = []
        for s_pk in subject_list:
            subj = Subject.objects.get(pk=int(s_pk))
            subject_objects.append(subj)
            subject_group.subjects.add(subj)

        subject_group.save()
        return redirect('result:subject_groups')
    ctx = {
        'departments': departments,
        'semesters': semesters,
        'subjects': subjects,
    }
    return render(request, 'result/create_subject_groups.html', ctx)


@user_passes_test(user_is_verified)
def subject_group_list(request):
    subject_groups = SubjectGroup.objects.all()
    ctx = {
        'subject_groups': subject_groups,
    }
    return render(request, 'result/subject_group_list.html', ctx)


# Teacher-specific views for mark entry
@user_passes_test(user_is_teacher)
def teacher_dashboard(request):
    """ Teacher dashboard showing their assigned subjects and quick actions """
    teacher = request.user.teacher_profile
    assigned_subjects = Subject.objects.filter(instructor=teacher)
    recent_results = Result.objects.filter(
        subject__in=assigned_subjects
    ).order_by('-created')[:5]
    recent_attendance = Attendance.objects.filter(
        subject__in=assigned_subjects
    ).order_by('-date')[:5]
    
    ctx = {
        'teacher': teacher,
        'assigned_subjects': assigned_subjects,
        'recent_results': recent_results,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'result/teacher_dashboard.html', ctx)


@user_passes_test(user_is_teacher)
def teacher_mark_entry(request):
    """ Teacher-specific mark entry view """
    teacher = request.user.teacher_profile
    assigned_subjects = Subject.objects.filter(instructor=teacher)
    
    if request.method == 'POST':
        if 'form-TOTAL_FORMS' in request.POST:
            formset = ResultFormSet(
                request.POST,
                queryset=Result.objects.none()
            )
            if formset.is_valid():
                pending_updates = []
                for row_form in formset:
                    cleaned_data = row_form.cleaned_data
                    if not cleaned_data:
                        continue
                    student = cleaned_data['student']
                    semester = cleaned_data['semester']
                    subject = cleaned_data['subject']
                    practical_marks = cleaned_data.get('practical_marks')
                    theory_marks = cleaned_data.get('theory_marks')

                    if subject not in assigned_subjects:
                        row_form.add_error(None, 'You are not assigned to one or more selected subjects.')
                        continue
                    if practical_marks is not None and (
                        practical_marks < 0 or practical_marks > subject.practical_marks
                    ):
                        row_form.add_error('practical_marks', f'Enter 0-{subject.practical_marks}.')
                        continue
                    if theory_marks is not None and (
                        theory_marks < 0 or theory_marks > subject.theory_marks
                    ):
                        row_form.add_error('theory_marks', f'Enter 0-{subject.theory_marks}.')
                        continue
                    pending_updates.append({
                        'student': student,
                        'semester': semester,
                        'subject': subject,
                        'practical_marks': practical_marks,
                        'theory_marks': theory_marks,
                    })

                if all([not item.errors for item in formset.forms]):
                    saved_count = len(pending_updates)
                    with transaction.atomic():
                        for item in pending_updates:
                            Result.objects.update_or_create(
                                student=item['student'],
                                semester=item['semester'],
                                subject=item['subject'],
                                defaults={
                                    'practical_marks': item['practical_marks'],
                                    'theory_marks': item['theory_marks'],
                                }
                            )
                    messages.success(request, f'Saved marks for {saved_count} student(s).')
                    return redirect('result:teacher_view_results')
            form = TeacherMarkEntryForm()
            ctx = {
                'teacher': teacher,
                'form': form,
                'formset': formset,
                'assigned_subjects': assigned_subjects,
            }
            return render(request, 'result/teacher_mark_entry.html', ctx)

        form = TeacherMarkEntryForm(request.POST)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            subject = form.cleaned_data['subject']
            
            # Check if teacher is assigned to this subject
            if subject not in assigned_subjects:
                messages.error(request, "You are not assigned to this subject.")
                return redirect('result:teacher_mark_entry')
            
            # Get students enrolled in this semester and subject's department
            students = Student.objects.filter(
                semester=semester,
                admission_student__choosen_department=subject.department_choice
            ).order_by('admission_student__name')
            
            # Prepare initial data for formset
            initial_data = []
            for student in students:
                # Check if result already exists
                existing_result = Result.objects.filter(
                    student=student,
                    semester=semester,
                    subject=subject
                ).first()
                
                if existing_result:
                    initial_data.append({
                        'student': student,
                        'semester': semester,
                        'subject': subject,
                        'practical_marks': existing_result.practical_marks,
                        'theory_marks': existing_result.theory_marks,
                    })
                else:
                    initial_data.append({
                        'student': student,
                        'semester': semester,
                        'subject': subject,
                    })
            
            formset = ResultFormSet(
                queryset=Result.objects.none(),
                initial=initial_data
            )
            ctx = {
                'teacher': teacher,
                'form': form,
                'formset': formset,
                'assigned_subjects': assigned_subjects,
            }
            return render(request, 'result/teacher_mark_entry.html', ctx)
    else:
        form = TeacherMarkEntryForm()
        ctx = {
            'teacher': teacher,
            'form': form,
            'assigned_subjects': assigned_subjects,
        }
    return render(request, 'result/teacher_mark_entry.html', ctx)


@user_passes_test(user_is_teacher)
def teacher_attendance_entry(request):
    """ Teacher-specific attendance entry view """
    teacher = request.user.teacher_profile
    assigned_subjects = Subject.objects.filter(instructor=teacher)
    
    if request.method == 'POST':
        form = TeacherAttendanceEntryForm(request.POST)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            subject = form.cleaned_data['subject']
            date = form.cleaned_data['date']
            
            # Check if teacher is assigned to this subject
            if subject not in assigned_subjects:
                messages.error(request, "You are not assigned to this subject.")
                return redirect('result:teacher_attendance_entry')
            
            # Get students enrolled in this semester and subject's department
            students = Student.objects.filter(
                semester=semester,
                admission_student__choosen_department=subject.department_choice
            ).order_by('admission_student__name')
            
            # Prepare initial data for formset
            initial_data = []
            for student in students:
                # Check if attendance already exists for this date
                existing_attendance = Attendance.objects.filter(
                    student=student,
                    subject=subject,
                    semester=semester,
                    date=date
                ).first()
                
                if existing_attendance:
                    initial_data.append({
                        'student': student,
                        'subject': subject,
                        'semester': semester,
                        'date': date,
                        'status': existing_attendance.status,
                    })
                else:
                    initial_data.append({
                        'student': student,
                        'subject': subject,
                        'semester': semester,
                        'date': date,
                    })
            
            formset = AttendanceFormSet(
                queryset=Attendance.objects.none(),
                initial=initial_data
            )
            ctx = {
                'form': form,
                'formset': formset,
                'assigned_subjects': assigned_subjects,
            }
            return render(request, 'result/teacher_attendance_entry.html', ctx)
    else:
        form = TeacherAttendanceEntryForm()
        ctx = {
            'form': form,
            'assigned_subjects': assigned_subjects,
        }
    return render(request, 'result/teacher_attendance_entry.html', ctx)


@user_passes_test(user_is_teacher)
def teacher_view_results(request):
    """ Teacher can view results for their assigned subjects """
    teacher = request.user.teacher_profile
    assigned_subjects = Subject.objects.filter(instructor=teacher)
    results = Result.objects.filter(subject__in=assigned_subjects).order_by('-created')
    
    ctx = {
        'results': results,
        'assigned_subjects': assigned_subjects,
    }
    return render(request, 'result/teacher_view_results.html', ctx)


@user_passes_test(user_is_teacher)
def teacher_view_attendance(request):
    """ Teacher can view attendance for their assigned subjects """
    teacher = request.user.teacher_profile
    assigned_subjects = Subject.objects.filter(instructor=teacher)
    attendance_records = Attendance.objects.filter(subject__in=assigned_subjects).order_by('-date')
    
    ctx = {
        'attendance_records': attendance_records,
        'assigned_subjects': assigned_subjects,
    }
    return render(request, 'result/teacher_view_attendance.html', ctx)