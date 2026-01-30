"""
Forms for schools, users, and other app models.

Authentication forms (LoginForm, RegistrationForm, UserApplicationForm) 
have been moved to authentication.forms module.

Import from authentication.forms:
    from authentication.forms import LoginForm, RegistrationForm, UserApplicationForm
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    School, User, ClassSection, Subject, GradingScale, StudentEnrollment,
    GradingPeriod, Grade, Attendance, UserApplication, SchoolProfile,
    SupportTicket, ReportTemplate, TemplateSection, TemplateField
)
from .base_forms import (
    BaseSchoolForm, BaseTeacherFilterForm, BaseStudentFilterForm, BaseMultiSchoolFilterForm
)
from authentication.forms import UserApplicationForm


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Enter school name',
                'autofocus': True,
                'required': True
            })
        }
        help_texts = {
            'name': 'Enter the full name of the school. This name must be unique.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom validation and styling
        self.fields['name'].widget.attrs.update({
            'maxlength': '255'
        })

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError('School name is required.')
        
        # Strip whitespace and normalize
        name = name.strip()
        if len(name) < 2:
            raise forms.ValidationError('School name must be at least 2 characters long.')
        if len(name) > 255:
            raise forms.ValidationError('School name cannot exceed 255 characters.')
        
        # Check for duplicates (case-insensitive)
        existing_school = School.objects.filter(name__iexact=name)
        if self.instance.pk:
            existing_school = existing_school.exclude(pk=self.instance.pk)
        
        if existing_school.exists():
            raise forms.ValidationError('A school with this name already exists. Please choose a different name.')
        
        return name


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
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # Super admin can see all schools, others only their school
        if self.request and self.request.user.role != 'super_admin':
            self.fields['school'].queryset = School.objects.filter(id=self.request.user.school.id)
        self.fields['role'].choices = User.ROLE_CHOICES

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ClassSectionForm(BaseTeacherFilterForm):
    class Meta:
        model = ClassSection
        fields = ['name', 'grade_level', 'teacher', 'school']


class SubjectForm(BaseSchoolForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description', 'school']


class GradingScaleForm(BaseSchoolForm):
    class Meta:
        model = GradingScale
        fields = ['name', 'scale_type', 'ranges', 'school']
        widgets = {
            'ranges': forms.Textarea(attrs={'rows': 10, 'placeholder': 'JSON grading ranges e.g., [{"grade": "A", "min_score": 90, "max_score": 100}]'}),
        }


class StudentEnrollmentForm(BaseMultiSchoolFilterForm):
    class Meta:
        model = StudentEnrollment
        fields = ['student', 'class_section', 'school']


class GradingPeriodForm(BaseSchoolForm):
    class Meta:
        model = GradingPeriod
        fields = ['name', 'school', 'start_date', 'end_date']


class GradeForm(BaseMultiSchoolFilterForm):
    auto_calculate = forms.BooleanField(
        required=False, initial=True,
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
        if self.instance and self.instance.pk:
            self.fields['auto_calculate'].initial = not self.instance.is_override

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        letter_grade = cleaned_data.get('letter_grade')
        auto_calculate = cleaned_data.get('auto_calculate', True)
        school = cleaned_data.get('school') or (self.request.user.school if hasattr(self, 'request') else None)

        cleaned_data['is_override'] = not auto_calculate

        if auto_calculate and score is not None:
            try:
                grading_scale = GradingScale.objects.filter(school=school).first()
                if grading_scale and grading_scale.ranges:
                    sorted_ranges = sorted(grading_scale.ranges, key=lambda x: x.get('min_score', 0), reverse=True)
                    for grade_range in sorted_ranges:
                        min_score = grade_range.get('min_score', 0)
                        max_score = grade_range.get('max_score', 100)
                        if min_score <= score <= max_score:
                            cleaned_data['letter_grade'] = grade_range.get('grade', '')
                            break
            except (GradingScale.DoesNotExist, KeyError, TypeError, AttributeError):
                pass

        return cleaned_data


class AttendanceForm(BaseMultiSchoolFilterForm):
    class Meta:
        model = Attendance
        fields = ['student', 'class_section', 'date', 'status', 'notes', 'school']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }







class ApplicationReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Optional notes for rejection"
    )


class SchoolProfileForm(forms.ModelForm):
    """Form for managing school branding and white-label features"""
    
    class Meta:
        model = SchoolProfile
        fields = [
            'logo', 'favicon', 'primary_color', 'secondary_color', 'accent_color',
            'custom_domain', 'address', 'phone', 'email', 'website',
            'report_header', 'report_footer', 'report_signature',
            'enable_analytics', 'enable_support_portal', 'enable_custom_templates',
            'default_report_template'
        ]
        widgets = {
            'primary_color': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'form-control form-control-color'
            }),
            'secondary_color': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'form-control form-control-color'
            }),
            'accent_color': forms.TextInput(attrs={
                'type': 'color', 
                'class': 'form-control form-control-color'
            }),
            'address': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control form-control-modern'
            }),
            'report_header': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., "Green Valley High School Report Card"'
            }),
            'report_footer': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., "Prepared by the Academic Department"'
            }),
            'report_signature': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., "Dr. Sarah Johnson, Principal"'
            }),
            'custom_domain': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., schoolname.reportcardapp.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'https://yourschool.edu'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': '+1 (555) 123-4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'info@yourschool.edu'
            }),
        }
        help_texts = {
            'logo': 'Upload your school logo (recommended size: 300x300px)',
            'favicon': 'Upload your school favicon (recommended size: 32x32px)',
            'primary_color': 'Main brand color for headers and primary buttons',
            'secondary_color': 'Secondary brand color for gradients and accents',
            'accent_color': 'Accent color for highlights and important elements',
            'custom_domain': 'Custom domain for your school (requires SSL certificate)',
            'default_report_template': 'Default template used for generating report cards',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional since this is for customization
        for field_name, field in self.fields.items():
            field.required = False


class SupportTicketForm(forms.ModelForm):
    """Form for creating and managing support tickets"""
    
    class Meta:
        model = SupportTicket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Brief description of your issue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-modern',
                'rows': 6,
                'placeholder': 'Please describe your issue in detail...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
        }
        help_texts = {
            'title': 'A brief summary of your support request',
            'description': 'Provide as much detail as possible about your issue',
            'category': 'Select the category that best describes your issue',
            'priority': 'Choose the urgency level of your request',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Set priority choices with custom labels
        self.fields['priority'].choices = [
            ('low', 'Low - Can wait'),
            ('medium', 'Medium - Within 24 hours'),
            ('high', 'High - Within 4 hours'),
            ('urgent', 'Urgent - Immediate attention required')
        ]
        
        # Set category choices
        self.fields['category'].choices = [
            ('', 'Select a category...'),
            ('technical', 'Technical Issue'),
            ('account', 'Account Management'),
            ('feature_request', 'Feature Request'),
            ('billing', 'Billing/Payment'),
            ('training', 'Training/Documentation'),
            ('other', 'Other')
        ]


class SupportTicketAdminForm(forms.ModelForm):
    """Admin form for managing support tickets"""
    
    class Meta:
        model = SupportTicket
        fields = ['status', 'priority', 'assigned_to', 'resolved_by']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to to only show admin/super_admin users
        self.fields['assigned_to'].queryset = User.objects.filter(
            role__in=['admin', 'super_admin']
        ).order_by('last_name', 'first_name')
        
        # Set priority choices
        self.fields['priority'].choices = [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ]


class ReportTemplateForm(forms.ModelForm):
    """Form for creating and editing report templates"""
    
    create_default_sections = forms.BooleanField(
        required=False,
        initial=True,
        label="Create default sections",
        help_text="Check to automatically create standard sections (Header, Student Info, Academic Performance, etc.)"
    )
    
    class Meta:
        model = ReportTemplate
        fields = [
            'name', 'template_type', 'header_background_color', 'header_text_color',
            'font_family', 'font_size', 'heading_font_size', 'primary_color', 
            'secondary_color', 'border_style', 'border_color', 'report_title',
            'grading_period_label', 'teacher_label', 'principal_label', 'footer_text',
            'show_school_stamp', 'show_contact_info', 'include_student_photo',
            'include_teacher_comments', 'include_principal_signature', 'include_grading_scale',
            'include_attendance_summary', 'custom_fields'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Enter template name'
            }),
            'template_type': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'header_background_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'header_text_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'font_family': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'font_size': forms.NumberInput(attrs={
                'class': 'form-control form-control-modern',
                'min': '8',
                'max': '24'
            }),
            'heading_font_size': forms.NumberInput(attrs={
                'class': 'form-control form-control-modern',
                'min': '10',
                'max': '36'
            }),
            'primary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'secondary_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'border_style': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'border_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'report_title': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., Report Card'
            }),
            'grading_period_label': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., Grading Period'
            }),
            'teacher_label': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., Class Teacher'
            }),
            'principal_label': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'e.g., Principal'
            }),
            'footer_text': forms.Textarea(attrs={
                'class': 'form-control form-control-modern',
                'rows': 3,
                'placeholder': 'Custom footer text for report cards'
            }),
            'custom_fields': forms.Textarea(attrs={
                'class': 'form-control form-control-modern',
                'rows': 4,
                'placeholder': 'JSON format for custom fields, e.g., {"field1": "value1"}'
            }),
        }
        help_texts = {
            'name': 'A descriptive name for this report template',
            'template_type': 'Select the appropriate template type for your school level',
            'font_size': 'Base font size for the report card content',
            'heading_font_size': 'Font size for section headings',
            'footer_text': 'Additional text to appear at the bottom of report cards',
            'custom_fields': 'Optional custom fields in JSON format that can be used in the template',
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Set font family choices
        self.fields['font_family'].choices = [
            ('Arial, sans-serif', 'Arial'),
            ('Times New Roman, serif', 'Times New Roman'),
            ('Georgia, serif', 'Georgia'),
            ('Verdana, sans-serif', 'Verdana'),
            ('Helvetica, sans-serif', 'Helvetica'),
            ('Courier New, monospace', 'Courier New'),
        ]
        
        # Set border style choices
        self.fields['border_style'].choices = [
            ('solid', 'Solid'),
            ('dashed', 'Dashed'),
            ('dotted', 'Dotted'),
            ('none', 'None'),
        ]
        
        # Filter school choices based on user permissions
        if self.request:
            if self.request.user.role == 'super_admin':
                pass  # Can see all schools
            else:
                # For template forms, school is typically set automatically
                # based on the user's school, so we might not show this field
                pass

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Strip whitespace and normalize
            name = name.strip()
            if len(name) < 2:
                raise forms.ValidationError('Template name must be at least 2 characters long.')
            if len(name) > 200:
                raise forms.ValidationError('Template name cannot exceed 200 characters.')
        
        return name

    def clean_custom_fields(self):
        custom_fields = self.cleaned_data.get('custom_fields')
        if custom_fields:
            try:
                # Validate JSON format
                import json
                json.loads(custom_fields)
            except json.JSONDecodeError:
                raise forms.ValidationError('Custom fields must be valid JSON format.')
        return custom_fields


class TemplateSectionForm(forms.ModelForm):
    """Form for creating and editing template sections"""
    
    class Meta:
        model = TemplateSection
        fields = [
            'section_type', 'title', 'order', 'is_visible', 'css_class',
            'show_border', 'background_color', 'text_color', 'content_template'
        ]
        widgets = {
            'section_type': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Section title'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control form-control-modern',
                'min': '0'
            }),
            'css_class': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Optional CSS class'
            }),
            'background_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'text_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
            'content_template': forms.Textarea(attrs={
                'class': 'form-control form-control-modern',
                'rows': 6,
                'placeholder': 'HTML template for this section content'
            }),
        }
        help_texts = {
            'section_type': 'Type of section (determines default content)',
            'title': 'Display title for this section',
            'order': 'Order in which sections appear (lower numbers first)',
            'css_class': 'Optional custom CSS class for styling',
            'content_template': 'HTML template with placeholders for dynamic content',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set section type choices
        self.fields['section_type'].choices = [
            ('header', 'Header'),
            ('student_info', 'Student Information'),
            ('academic_performance', 'Academic Performance'),
            ('attendance', 'Attendance'),
            ('teacher_comments', 'Teacher Comments'),
            ('principal_comments', 'Principal Comments'),
            ('footer', 'Footer'),
        ]

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) > 100:
                raise forms.ValidationError('Section title cannot exceed 100 characters.')
        return title


class TemplateFieldForm(forms.ModelForm):
    """Form for creating and editing template custom fields"""
    
    class Meta:
        model = TemplateField
        fields = [
            'name', 'field_key', 'field_type', 'order', 'is_required', 'options', 'default_value'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Field display name'
            }),
            'field_key': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Internal field key (e.g., field_1)'
            }),
            'field_type': forms.Select(attrs={
                'class': 'form-control form-control-modern'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control form-control-modern',
                'min': '0'
            }),
            'options': forms.Textarea(attrs={
                'class': 'form-control form-control-modern',
                'rows': 3,
                'placeholder': 'JSON options for select fields, e.g., ["Option 1", "Option 2"]'
            }),
            'default_value': forms.TextInput(attrs={
                'class': 'form-control form-control-modern',
                'placeholder': 'Default value for this field'
            }),
        }
        help_texts = {
            'name': 'Display name for this custom field',
            'field_key': 'Internal identifier for the field (must be unique)',
            'field_type': 'Type of input field',
            'options': 'JSON array of options for dropdown fields',
            'default_value': 'Default value when field is empty',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field type choices
        self.fields['field_type'].choices = [
            ('text', 'Text'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('boolean', 'Yes/No'),
            ('select', 'Dropdown'),
        ]

    def clean_field_key(self):
        field_key = self.cleaned_data.get('field_key')
        if field_key:
            field_key = field_key.strip()
            # Basic validation for field key format
            if not field_key.replace('_', '').replace('-', '').isalnum():
                raise forms.ValidationError('Field key can only contain letters, numbers, underscores, and hyphens.')
            if len(field_key) > 50:
                raise forms.ValidationError('Field key cannot exceed 50 characters.')
        return field_key

    def clean_options(self):
        options = self.cleaned_data.get('options')
        if options and self.cleaned_data.get('field_type') == 'select':
            try:
                # Validate JSON format for options
                import json
                parsed_options = json.loads(options)
                if not isinstance(parsed_options, list):
                    raise forms.ValidationError('Options must be a JSON array.')
            except json.JSONDecodeError:
                raise forms.ValidationError('Options must be valid JSON format.')
        return options


