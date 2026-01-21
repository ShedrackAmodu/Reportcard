from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import School, User, ClassSection, Subject, GradingScale, StudentEnrollment, GradingPeriod, Grade, Attendance


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'theme', 'report_template']
        widgets = {
            'theme': forms.Textarea(attrs={'rows': 10, 'placeholder': 'JSON theme configuration'}),
            'report_template': forms.Textarea(attrs={'rows': 15, 'placeholder': 'JSON report card template'}),
        }


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text="Leave blank to keep current password"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'school']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Super admin can see all schools, others only their school
        if hasattr(self, 'request') and self.request.user.role != 'super_admin':
            self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)
        self.fields['role'].choices = User.ROLE_CHOICES

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ClassSectionForm(forms.ModelForm):
    class Meta:
        model = ClassSection
        fields = ['name', 'grade_level', 'teacher', 'school']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter schools and teachers based on user role
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass  # Can see all schools and teachers
            else:
                self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)
                # Filter teachers to only those from the same school
                self.fields['teacher'].queryset = User.objects.filter(school=self.request.user.school, role='teacher')


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description', 'school']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass
            else:
                self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)


class GradingScaleForm(forms.ModelForm):
    class Meta:
        model = GradingScale
        fields = ['name', 'scale_type', 'ranges', 'school']
        widgets = {
            'ranges': forms.Textarea(attrs={'rows': 10, 'placeholder': 'JSON grading ranges e.g., [{"grade": "A", "min_score": 90, "max_score": 100}]'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass
            else:
                self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)


class StudentEnrollmentForm(forms.ModelForm):
    class Meta:
        model = StudentEnrollment
        fields = ['student', 'class_section', 'school']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                # Filter students and classes by school when selected
                if self.instance and self.instance.school:
                    self.fields['student'].queryset = User.objects.filter(school=self.instance.school, role='student')
                    self.fields['class_section'].queryset = ClassSection.objects.filter(school=self.instance.school)
                else:
                    self.fields['student'].queryset = User.objects.filter(role='student')
                    self.fields['class_section'].queryset = ClassSection.objects.all()
            else:
                school = self.request.user.school
                self.fields['student'].queryset = User.objects.filter(school=school, role='student')
                self.fields['class_section'].queryset = ClassSection.objects.filter(school=school)
                self.fields['school'].initial = school
                self.fields['school'].widget = forms.HiddenInput()


class GradingPeriodForm(forms.ModelForm):
    class Meta:
        model = GradingPeriod
        fields = ['name', 'school', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass
            else:
                self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ['student', 'subject', 'grading_period', 'score', 'letter_grade', 'comments', 'school']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass
            else:
                school = self.request.user.school
                self.fields['student'].queryset = User.objects.filter(school=school, role='student')
                self.fields['subject'].queryset = Subject.objects.filter(school=school)
                self.fields['grading_period'].queryset = GradingPeriod.objects.filter(school=school)
                self.fields['school'].initial = school
                self.fields['school'].widget = forms.HiddenInput()


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'class_section', 'date', 'status', 'notes', 'school']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'request'):
            if self.request.user.role == 'super_admin':
                pass
            else:
                school = self.request.user.school
                self.fields['student'].queryset = User.objects.filter(school=school, role='student')
                self.fields['class_section'].queryset = ClassSection.objects.filter(school=school)
                self.fields['school'].initial = school
                self.fields['school'].widget = forms.HiddenInput()
