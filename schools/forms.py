from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import School, User, ClassSection, Subject, GradingScale, StudentEnrollment, GradingPeriod, Grade, Attendance, UserApplication


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
    auto_calculate = forms.BooleanField(
        required=False,
        initial=True,
        label="Auto-calculate letter grade",
        help_text="Uncheck to manually set letter grade (override)"
    )

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

        # If editing existing grade, show override status
        if self.instance and self.instance.pk:
            self.fields['auto_calculate'].initial = not self.instance.is_override

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        letter_grade = cleaned_data.get('letter_grade')
        auto_calculate = cleaned_data.get('auto_calculate', True)
        school = cleaned_data.get('school') or (self.request.user.school if hasattr(self, 'request') else None)

        # Set override flag based on auto_calculate
        cleaned_data['is_override'] = not auto_calculate

        # If auto-calculate is enabled and score is provided, calculate letter grade
        if auto_calculate and score is not None:
            try:
                # Get the first grading scale for the school
                grading_scale = GradingScale.objects.filter(school=school).first()
                if grading_scale and grading_scale.ranges:
                    # Sort ranges by min_score descending to check highest grades first
                    sorted_ranges = sorted(grading_scale.ranges, key=lambda x: x.get('min_score', 0), reverse=True)
                    for grade_range in sorted_ranges:
                        min_score = grade_range.get('min_score', 0)
                        max_score = grade_range.get('max_score', 100)
                        if min_score <= score <= max_score:
                            cleaned_data['letter_grade'] = grade_range.get('grade', '')
                            break
            except (GradingScale.DoesNotExist, KeyError, TypeError, AttributeError):
                pass  # Keep letter_grade as provided if calculation fails

        # If manual override is enabled, keep the manually entered letter grade
        elif not auto_calculate and letter_grade:
            # Keep the manually entered grade
            pass

        return cleaned_data


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


class UserApplicationForm(forms.ModelForm):
    class Meta:
        model = UserApplication
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'school']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter role choices - students can register directly, others need approval
        self.fields['role'].choices = [
            choice for choice in User.ROLE_CHOICES
            if choice[0] in ['admin', 'teacher', 'student']
        ]

        # Super admin can see all schools, others only their school
        if hasattr(self, 'request') and self.request.user.role != 'super_admin':
            self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)


class ApplicationReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Optional notes for rejection"
    )


class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['report_template']
        widgets = {
            'report_template': forms.Textarea(attrs={
                'rows': 20,
                'placeholder': '''Example template structure:
{
  "header": {
    "school_name": "{{ school.name }}",
    "title": "Report Card",
    "academic_year": "2024-2025"
  },
  "student_info": {
    "name": "{{ student.get_full_name }}",
    "id": "{{ student.username }}",
    "class": "{{ enrollment.class_section.name }}"
  },
  "grades_table": {
    "columns": ["Subject", "Score", "Grade", "Comments"],
    "rows": [
      {% for grade in grades %}
      ["{{ grade.subject.name }}", "{{ grade.score }}", "{{ grade.letter_grade }}", "{{ grade.comments }}"]{% if not forloop.last %},{% endif %}
      {% endfor %}
    ]
  },
  "footer": {
    "generated_date": "{{ now|date:'M d, Y' }}",
    "signature": "School Administration"
  }
}'''
            }),
        }
