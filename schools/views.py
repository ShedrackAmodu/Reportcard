from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['role'] = user.role
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from .models import School, User, ClassSection, Subject, GradingScale, StudentEnrollment, GradingPeriod, Grade, Attendance
from .serializers import (
    SchoolSerializer, UserSerializer, ClassSectionSerializer,
    SubjectSerializer, GradingScaleSerializer, StudentEnrollmentSerializer, GradingPeriodSerializer,
    GradeSerializer, AttendanceSerializer
)
from .permissions import (
    IsSuperAdmin, IsSchoolAdmin, IsSchoolMember, IsOwnerOrSchoolAdmin,
    IsTeacher, IsStudent, IsStudentOwner, IsTeacherOrAdmin
)


class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return School.objects.all()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSchoolAdmin]

    def get_queryset(self):
        if self.request.user.role == 'super_admin':
            return User.objects.all()
        return User.objects.filter(school=self.request.school) if self.request.school else User.objects.none()

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            # Allow students to view their own profile, teachers/admins to view school users
            return [IsStudent()]
        return [IsSchoolAdmin()]


class ClassSectionViewSet(viewsets.ModelViewSet):
    queryset = ClassSection.objects.all()
    serializer_class = ClassSectionSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return ClassSection.objects.filter(school=self.request.school) if self.request.school else ClassSection.objects.none()


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return Subject.objects.filter(school=self.request.school) if self.request.school else Subject.objects.none()


class GradingScaleViewSet(viewsets.ModelViewSet):
    queryset = GradingScale.objects.all()
    serializer_class = GradingScaleSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return GradingScale.objects.filter(school=self.request.school) if self.request.school else GradingScale.objects.none()


class GradingPeriodViewSet(viewsets.ModelViewSet):
    queryset = GradingPeriod.objects.all()
    serializer_class = GradingPeriodSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return GradingPeriod.objects.filter(school=self.request.school) if self.request.school else GradingPeriod.objects.none()


class StudentEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = StudentEnrollment.objects.all()
    serializer_class = StudentEnrollmentSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return StudentEnrollment.objects.filter(school=self.request.school) if self.request.school else StudentEnrollment.objects.none()

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            # Students can view their own enrollments
            return [IsStudent(), IsStudentOwner()]
        return [IsTeacherOrAdmin()]


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return Grade.objects.filter(school=self.request.school) if self.request.school else Grade.objects.none()

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            # Students can view their own grades
            return [IsStudent(), IsStudentOwner()]
        return [IsTeacherOrAdmin()]


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        return Attendance.objects.filter(school=self.request.school) if self.request.school else Attendance.objects.none()

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            # Students can view their own attendance
            return [IsStudent(), IsStudentOwner()]
        return [IsTeacherOrAdmin()]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_view(request):
    last_sync_str = request.GET.get('last_sync')
    if not last_sync_str:
        return Response({'error': 'last_sync parameter required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
    except ValueError:
        return Response({'error': 'Invalid last_sync format'}, status=status.HTTP_400_BAD_REQUEST)

    data = {}
    models = [
        (School, SchoolSerializer),
        (User, UserSerializer),
        (ClassSection, ClassSectionSerializer),
        (Subject, SubjectSerializer),
        (GradingScale, GradingScaleSerializer),
        (GradingPeriod, GradingPeriodSerializer),
        (StudentEnrollment, StudentEnrollmentSerializer),
        (Grade, GradeSerializer),
        (Attendance, AttendanceSerializer),
    ]

    for model, serializer_class in models:
        queryset = model.objects.filter(updated_at__gt=last_sync)
        if hasattr(model, 'school') and request.school:
            queryset = queryset.filter(school=request.school)
        elif model == School and request.user.role != 'super_admin':
            queryset = queryset.none()
        elif model == User and request.user.role != 'super_admin':
            queryset = queryset.filter(school=request.school) if request.school else queryset.none()

        serializer = serializer_class(queryset, many=True)
        data[model.__name__.lower()] = serializer.data

    return Response(data)


# Web Views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    from .models import School
    schools = School.objects.all()

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        school_id = request.POST.get('school')
        if form.is_valid():
            user = form.get_user()
            # For multi-tenancy, set school in session if selected
            if school_id:
                try:
                    selected_school = School.objects.get(id=school_id)
                    request.session['school_id'] = selected_school.id
                except School.DoesNotExist:
                    pass
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'schools/login.html', {'form': form, 'schools': schools})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    from .forms import UserForm
    from .models import School
    schools = School.objects.all()

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserForm()

    return render(request, 'schools/register.html', {
        'form': form,
        'schools': schools,
        'title': 'Register for SchoolSync'
    })


@login_required
def dashboard_view(request):
    user = request.user
    context = {
        'user': user,
        'role': user.role,
    }

    if user.role == 'super_admin':
        context['schools_count'] = School.objects.count()
        context['users_count'] = User.objects.count()
    elif user.school:
        context['school'] = user.school
        context['classes_count'] = ClassSection.objects.filter(school=user.school).count()
        context['subjects_count'] = Subject.objects.filter(school=user.school).count()
        context['students_count'] = StudentEnrollment.objects.filter(school=user.school).count()

    return render(request, 'schools/dashboard.html', context)


def landing_view(request):
    return render(request, 'schools/landing.html', {
        'title': 'SchoolSync - Multi-Tenant Report Card System'
    })


@login_required
def school_switch(request):
    if request.user.role != 'super_admin':
        messages.error(request, 'Access denied. Super admin required.')
        return redirect('dashboard')

    # Handle quick switch via GET parameter
    school_id_param = request.GET.get('school_id')
    if school_id_param is not None:
        if school_id_param:
            request.session['school_id'] = int(school_id_param)
            try:
                school = School.objects.get(id=school_id_param)
                messages.success(request, f'Switched to school: {school.name}')
            except School.DoesNotExist:
                messages.error(request, 'School not found')
        else:
            request.session.pop('school_id', None)
            messages.success(request, 'Switched to global view')
        return redirect('dashboard')

    if request.method == 'POST':
        school_id = request.POST.get('school_id')
        if school_id:
            request.session['school_id'] = int(school_id)
            school = School.objects.get(id=school_id)
            messages.success(request, f'Switched to school: {school.name}')
        else:
            request.session.pop('school_id', None)
            messages.success(request, 'Switched to global view')
        return redirect('dashboard')

    schools = School.objects.all()
    current_school_id = request.session.get('school_id')
    current_school = None
    if current_school_id:
        try:
            current_school = School.objects.get(id=current_school_id)
        except School.DoesNotExist:
            pass

    return render(request, 'schools/school_switch.html', {
        'schools': schools,
        'current_school': current_school,
        'title': 'Switch School Context'
    })


# Management Views - Super Admin Only
@login_required
def school_list(request):
    if request.user.role != 'super_admin':
        messages.error(request, 'Access denied. Super admin required.')
        return redirect('dashboard')

    schools = School.objects.all().order_by('-created_at')
    return render(request, 'schools/school_list.html', {
        'schools': schools,
        'title': 'Manage Schools'
    })


@login_required
def school_create(request):
    if request.user.role != 'super_admin':
        messages.error(request, 'Access denied. Super admin required.')
        return redirect('dashboard')

    from .forms import SchoolForm
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'School created successfully.')
            return redirect('school_list')
    else:
        form = SchoolForm()
    return render(request, 'schools/school_form.html', {
        'form': form,
        'title': 'Create School'
    })


@login_required
def school_update(request, pk):
    if request.user.role != 'super_admin':
        messages.error(request, 'Access denied. Super admin required.')
        return redirect('dashboard')

    from .forms import SchoolForm
    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, 'School updated successfully.')
            return redirect('school_list')
    else:
        form = SchoolForm(instance=school)
    return render(request, 'schools/school_form.html', {
        'form': form,
        'school': school,
        'title': 'Edit School'
    })


@login_required
def school_delete(request, pk):
    if request.user.role != 'super_admin':
        messages.error(request, 'Access denied. Super admin required.')
        return redirect('dashboard')

    school = get_object_or_404(School, pk=pk)
    if request.method == 'POST':
        school.delete()
        messages.success(request, 'School deleted successfully.')
        return redirect('school_list')
    return render(request, 'schools/school_confirm_delete.html', {
        'school': school,
        'title': 'Delete School'
    })


# User Management Views
@login_required
def user_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    users = User.objects.all().order_by('-date_joined')
    if request.user.role == 'admin':
        users = users.filter(school=request.user.school)

    # Filter by role if specified
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'schools/user_list.html', {
        'users': users,
        'role_filter': role_filter,
        'title': 'Manage Users'
    })


@login_required
def user_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import UserForm
    if request.method == 'POST':
        form = UserForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
    else:
        form = UserForm()
        form.request = request
    return render(request, 'schools/user_form.html', {
        'form': form,
        'title': 'Create User'
    })


@login_required
def user_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import UserForm
    user_obj = get_object_or_404(User, pk=pk)

    # Check if admin can only edit users from their school
    if request.user.role == 'admin' and user_obj.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit users from other schools.')
        return redirect('user_list')

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user_list')
    else:
        form = UserForm(instance=user_obj)
        form.request = request
    return render(request, 'schools/user_form.html', {
        'form': form,
        'user_obj': user_obj,
        'title': 'Edit User'
    })


@login_required
def user_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    user_obj = get_object_or_404(User, pk=pk)

    # Check if admin can only delete users from their school
    if request.user.role == 'admin' and user_obj.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete users from other schools.')
        return redirect('user_list')

    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    return render(request, 'schools/user_confirm_delete.html', {
        'user_obj': user_obj,
        'title': 'Delete User'
    })


# Academic Management Views
@login_required
def class_section_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    class_sections = ClassSection.objects.all().order_by('school', 'name')
    if request.user.role == 'admin':
        class_sections = class_sections.filter(school=request.user.school)

    return render(request, 'schools/class_section_list.html', {
        'class_sections': class_sections,
        'title': 'Manage Class Sections'
    })


@login_required
def class_section_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import ClassSectionForm
    if request.method == 'POST':
        form = ClassSectionForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Class section created successfully.')
            return redirect('class_section_list')
    else:
        form = ClassSectionForm()
        form.request = request
    return render(request, 'schools/class_section_form.html', {
        'form': form,
        'title': 'Create Class Section'
    })


@login_required
def class_section_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import ClassSectionForm
    class_section = get_object_or_404(ClassSection, pk=pk)

    # Check if admin can only edit class sections from their school
    if request.user.role == 'admin' and class_section.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit class sections from other schools.')
        return redirect('class_section_list')

    if request.method == 'POST':
        form = ClassSectionForm(request.POST, instance=class_section)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Class section updated successfully.')
            return redirect('class_section_list')
    else:
        form = ClassSectionForm(instance=class_section)
        form.request = request
    return render(request, 'schools/class_section_form.html', {
        'form': form,
        'class_section': class_section,
        'title': 'Edit Class Section'
    })


@login_required
def class_section_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    class_section = get_object_or_404(ClassSection, pk=pk)

    # Check if admin can only delete class sections from their school
    if request.user.role == 'admin' and class_section.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete class sections from other schools.')
        return redirect('class_section_list')

    if request.method == 'POST':
        class_section.delete()
        messages.success(request, 'Class section deleted successfully.')
        return redirect('class_section_list')
    return render(request, 'schools/class_section_confirm_delete.html', {
        'class_section': class_section,
        'title': 'Delete Class Section'
    })


# Subject Management Views
@login_required
def subject_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    subjects = Subject.objects.all().order_by('school', 'name')
    if request.user.role == 'admin':
        subjects = subjects.filter(school=request.user.school)

    return render(request, 'schools/subject_list.html', {
        'subjects': subjects,
        'title': 'Manage Subjects'
    })


@login_required
def subject_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import SubjectForm
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject created successfully.')
            return redirect('subject_list')
    else:
        form = SubjectForm()
        form.request = request
    return render(request, 'schools/subject_form.html', {
        'form': form,
        'title': 'Create Subject'
    })


@login_required
def subject_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import SubjectForm
    subject = get_object_or_404(Subject, pk=pk)

    # Check if admin can only edit subjects from their school
    if request.user.role == 'admin' and subject.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit subjects from other schools.')
        return redirect('subject_list')

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully.')
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subject)
        form.request = request
    return render(request, 'schools/subject_form.html', {
        'form': form,
        'subject': subject,
        'title': 'Edit Subject'
    })


@login_required
def subject_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    subject = get_object_or_404(Subject, pk=pk)

    # Check if admin can only delete subjects from their school
    if request.user.role == 'admin' and subject.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete subjects from other schools.')
        return redirect('subject_list')

    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject deleted successfully.')
        return redirect('subject_list')
    return render(request, 'schools/subject_confirm_delete.html', {
        'subject': subject,
        'title': 'Delete Subject'
    })


# Grading Scale Management Views
@login_required
def grading_scale_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    grading_scales = GradingScale.objects.all().order_by('school', 'name')
    if request.user.role == 'admin':
        grading_scales = grading_scales.filter(school=request.user.school)

    return render(request, 'schools/grading_scale_list.html', {
        'grading_scales': grading_scales,
        'title': 'Manage Grading Scales'
    })


@login_required
def grading_scale_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import GradingScaleForm
    if request.method == 'POST':
        form = GradingScaleForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grading scale created successfully.')
            return redirect('grading_scale_list')
    else:
        form = GradingScaleForm()
        form.request = request
    return render(request, 'schools/grading_scale_form.html', {
        'form': form,
        'title': 'Create Grading Scale'
    })


@login_required
def grading_scale_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import GradingScaleForm
    grading_scale = get_object_or_404(GradingScale, pk=pk)

    # Check if admin can only edit grading scales from their school
    if request.user.role == 'admin' and grading_scale.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit grading scales from other schools.')
        return redirect('grading_scale_list')

    if request.method == 'POST':
        form = GradingScaleForm(request.POST, instance=grading_scale)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grading scale updated successfully.')
            return redirect('grading_scale_list')
    else:
        form = GradingScaleForm(instance=grading_scale)
        form.request = request
    return render(request, 'schools/grading_scale_form.html', {
        'form': form,
        'grading_scale': grading_scale,
        'title': 'Edit Grading Scale'
    })


@login_required
def grading_scale_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    grading_scale = get_object_or_404(GradingScale, pk=pk)

    # Check if admin can only delete grading scales from their school
    if request.user.role == 'admin' and grading_scale.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete grading scales from other schools.')
        return redirect('grading_scale_list')

    if request.method == 'POST':
        grading_scale.delete()
        messages.success(request, 'Grading scale deleted successfully.')
        return redirect('grading_scale_list')
    return render(request, 'schools/grading_scale_confirm_delete.html', {
        'grading_scale': grading_scale,
        'title': 'Delete Grading Scale'
    })


# Student Enrollment Management Views
@login_required
def enrollment_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    enrollments = StudentEnrollment.objects.all().select_related('student', 'class_section', 'school').order_by('school', 'class_section', 'student__last_name')
    if request.user.role == 'admin':
        enrollments = enrollments.filter(school=request.user.school)

    return render(request, 'schools/enrollment_list.html', {
        'enrollments': enrollments,
        'title': 'Manage Student Enrollments'
    })


@login_required
def enrollment_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import StudentEnrollmentForm
    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Student enrollment created successfully.')
            return redirect('enrollment_list')
    else:
        form = StudentEnrollmentForm()
        form.request = request
    return render(request, 'schools/enrollment_form.html', {
        'form': form,
        'title': 'Create Student Enrollment'
    })


@login_required
def enrollment_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import StudentEnrollmentForm
    enrollment = get_object_or_404(StudentEnrollment, pk=pk)

    # Check if admin can only edit enrollments from their school
    if request.user.role == 'admin' and enrollment.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit enrollments from other schools.')
        return redirect('enrollment_list')

    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST, instance=enrollment)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Student enrollment updated successfully.')
            return redirect('enrollment_list')
    else:
        form = StudentEnrollmentForm(instance=enrollment)
        form.request = request
    return render(request, 'schools/enrollment_form.html', {
        'form': form,
        'enrollment': enrollment,
        'title': 'Edit Student Enrollment'
    })


@login_required
def enrollment_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    enrollment = get_object_or_404(StudentEnrollment, pk=pk)

    # Check if admin can only delete enrollments from their school
    if request.user.role == 'admin' and enrollment.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete enrollments from other schools.')
        return redirect('enrollment_list')

    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, 'Student enrollment deleted successfully.')
        return redirect('enrollment_list')
    return render(request, 'schools/enrollment_confirm_delete.html', {
        'enrollment': enrollment,
        'title': 'Delete Student Enrollment'
    })


# Grading Period Management Views
@login_required
def grading_period_list(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    grading_periods = GradingPeriod.objects.all().order_by('school', 'start_date')
    if request.user.role == 'admin':
        grading_periods = grading_periods.filter(school=request.user.school)

    return render(request, 'schools/grading_period_list.html', {
        'grading_periods': grading_periods,
        'title': 'Manage Grading Periods'
    })


@login_required
def grading_period_create(request):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import GradingPeriodForm
    if request.method == 'POST':
        form = GradingPeriodForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grading period created successfully.')
            return redirect('grading_period_list')
    else:
        form = GradingPeriodForm()
        form.request = request
    return render(request, 'schools/grading_period_form.html', {
        'form': form,
        'title': 'Create Grading Period'
    })


@login_required
def grading_period_update(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    from .forms import GradingPeriodForm
    grading_period = get_object_or_404(GradingPeriod, pk=pk)

    # Check if admin can only edit grading periods from their school
    if request.user.role == 'admin' and grading_period.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit grading periods from other schools.')
        return redirect('grading_period_list')

    if request.method == 'POST':
        form = GradingPeriodForm(request.POST, instance=grading_period)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grading period updated successfully.')
            return redirect('grading_period_list')
    else:
        form = GradingPeriodForm(instance=grading_period)
        form.request = request
    return render(request, 'schools/grading_period_form.html', {
        'form': form,
        'grading_period': grading_period,
        'title': 'Edit Grading Period'
    })


@login_required
def grading_period_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin']:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard')

    grading_period = get_object_or_404(GradingPeriod, pk=pk)

    # Check if admin can only delete grading periods from their school
    if request.user.role == 'admin' and grading_period.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete grading periods from other schools.')
        return redirect('grading_period_list')

    if request.method == 'POST':
        grading_period.delete()
        messages.success(request, 'Grading period deleted successfully.')
        return redirect('grading_period_list')
    return render(request, 'schools/grading_period_confirm_delete.html', {
        'grading_period': grading_period,
        'title': 'Delete Grading Period'
    })


# Grade Management Views
@login_required
def grade_list(request):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    grades = Grade.objects.all().select_related('student', 'subject', 'grading_period', 'school').order_by('school', 'grading_period', 'subject', 'student__last_name')
    if request.user.role == 'admin':
        grades = grades.filter(school=request.user.school)
    elif request.user.role == 'teacher':
        grades = grades.filter(school=request.user.school, subject__class_sections__teacher=request.user).distinct()

    # Filter by grading period if specified
    grading_period_id = request.GET.get('grading_period')
    if grading_period_id:
        grades = grades.filter(grading_period_id=grading_period_id)

    return render(request, 'schools/grade_list.html', {
        'grades': grades,
        'grading_period_id': grading_period_id,
        'title': 'Manage Grades'
    })


@login_required
def grade_create(request):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    from .forms import GradeForm
    if request.method == 'POST':
        form = GradeForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade created successfully.')
            return redirect('grade_list')
    else:
        form = GradeForm()
        form.request = request
    return render(request, 'schools/grade_form.html', {
        'form': form,
        'title': 'Create Grade'
    })


@login_required
def grade_update(request, pk):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    from .forms import GradeForm
    grade = get_object_or_404(Grade, pk=pk)

    # Check permissions
    if request.user.role == 'admin' and grade.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit grades from other schools.')
        return redirect('grade_list')
    elif request.user.role == 'teacher' and not grade.subject.class_sections.filter(teacher=request.user).exists():
        messages.error(request, 'Access denied. Cannot edit grades for subjects you do not teach.')
        return redirect('grade_list')

    if request.method == 'POST':
        form = GradeForm(request.POST, instance=grade)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Grade updated successfully.')
            return redirect('grade_list')
    else:
        form = GradeForm(instance=grade)
        form.request = request
    return render(request, 'schools/grade_form.html', {
        'form': form,
        'grade': grade,
        'title': 'Edit Grade'
    })


@login_required
def grade_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    grade = get_object_or_404(Grade, pk=pk)

    # Check permissions
    if request.user.role == 'admin' and grade.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete grades from other schools.')
        return redirect('grade_list')
    elif request.user.role == 'teacher' and not grade.subject.class_sections.filter(teacher=request.user).exists():
        messages.error(request, 'Access denied. Cannot delete grades for subjects you do not teach.')
        return redirect('grade_list')

    if request.method == 'POST':
        grade.delete()
        messages.success(request, 'Grade deleted successfully.')
        return redirect('grade_list')
    return render(request, 'schools/grade_confirm_delete.html', {
        'grade': grade,
        'title': 'Delete Grade'
    })


# Attendance Management Views
@login_required
def attendance_list(request):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    attendances = Attendance.objects.all().select_related('student', 'class_section', 'school').order_by('school', 'date', 'class_section', 'student__last_name')
    if request.user.role == 'admin':
        attendances = attendances.filter(school=request.user.school)
    elif request.user.role == 'teacher':
        attendances = attendances.filter(school=request.user.school, class_section__teacher=request.user)

    # Filter by date if specified
    date_filter = request.GET.get('date')
    if date_filter:
        attendances = attendances.filter(date=date_filter)

    return render(request, 'schools/attendance_list.html', {
        'attendances': attendances,
        'date_filter': date_filter,
        'title': 'Manage Attendance'
    })


@login_required
def attendance_create(request):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    from .forms import AttendanceForm
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record created successfully.')
            return redirect('attendance_list')
    else:
        form = AttendanceForm()
        form.request = request
    return render(request, 'schools/attendance_form.html', {
        'form': form,
        'title': 'Create Attendance Record'
    })


@login_required
def attendance_update(request, pk):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    from .forms import AttendanceForm
    attendance = get_object_or_404(Attendance, pk=pk)

    # Check permissions
    if request.user.role == 'admin' and attendance.school != request.user.school:
        messages.error(request, 'Access denied. Cannot edit attendance from other schools.')
        return redirect('attendance_list')
    elif request.user.role == 'teacher' and attendance.class_section.teacher != request.user:
        messages.error(request, 'Access denied. Cannot edit attendance for classes you do not teach.')
        return redirect('attendance_list')

    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        form.request = request
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record updated successfully.')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=attendance)
        form.request = request
    return render(request, 'schools/attendance_form.html', {
        'form': form,
        'attendance': attendance,
        'title': 'Edit Attendance Record'
    })


@login_required
def attendance_delete(request, pk):
    if request.user.role not in ['super_admin', 'admin', 'teacher']:
        messages.error(request, 'Access denied. Insufficient privileges.')
        return redirect('dashboard')

    attendance = get_object_or_404(Attendance, pk=pk)

    # Check permissions
    if request.user.role == 'admin' and attendance.school != request.user.school:
        messages.error(request, 'Access denied. Cannot delete attendance from other schools.')
        return redirect('attendance_list')
    elif request.user.role == 'teacher' and attendance.class_section.teacher != request.user:
        messages.error(request, 'Access denied. Cannot delete attendance for classes you do not teach.')
        return redirect('attendance_list')

    if request.method == 'POST':
        attendance.delete()
        messages.success(request, 'Attendance record deleted successfully.')
        return redirect('attendance_list')
    return render(request, 'schools/attendance_confirm_delete.html', {
        'attendance': attendance,
        'title': 'Delete Attendance Record'
    })
