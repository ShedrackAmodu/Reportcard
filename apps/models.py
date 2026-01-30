from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class School(models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='unique_school_name'
            )
        ]

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', db_index=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class ClassSection(models.Model):
    name = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classes', limit_choices_to={'role': 'teacher'}, db_index=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    subjects = models.ManyToManyField(Subject, related_name='class_sections', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        teacher_name = self.teacher.get_full_name() if self.teacher else "No Teacher"
        return f"{self.name} - {teacher_name} - {self.school.name}"


class GradingScale(models.Model):
    name = models.CharField(max_length=100)
    scale_type = models.CharField(max_length=50, default='letter')  # e.g., 'letter', 'percentage'
    ranges = models.JSONField(default=list)  # list of {'grade': 'A', 'min_score': 90, 'max_score': 100}
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} ({self.scale_type}) - {self.school.name}"


class StudentEnrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', db_index=True)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='enrollments', db_index=True)
    enrollment_date = models.DateField(auto_now_add=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('student', 'class_section')

    def __str__(self):
        return f"{self.student.username} in {self.class_section.name}"


class GradingPeriod(models.Model):
    name = models.CharField(max_length=100)  # e.g., 'Q1', 'Semester 1', 'Term 1'
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date}) - {self.school.name}"


class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grades', db_index=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades', db_index=True)
    grading_period = models.ForeignKey(GradingPeriod, on_delete=models.CASCADE, related_name='grades', db_index=True)
    score = models.FloatField(null=True, blank=True)  # Numeric score (0-100)
    letter_grade = models.CharField(max_length=10, blank=True)  # Calculated letter grade
    comments = models.TextField(blank=True)
    is_override = models.BooleanField(default=False)  # Manual override of calculated grade
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('student', 'subject', 'grading_period')
        indexes = [
            models.Index(fields=['student', 'grading_period']),
            models.Index(fields=['subject', 'grading_period']),
            models.Index(fields=['school', 'grading_period']),
            models.Index(fields=['student', 'school']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.subject.name} - {self.grading_period.name}: {self.letter_grade or self.score}"

    def calculate_letter_grade(self):
        """Calculate letter grade based on school's grading scale"""
        if self.score is None:
            return None

        try:
            # Get the school's grading scale (use the first one, can be enhanced to select specific scale)
            grading_scale = GradingScale.objects.filter(school=self.school).first()
            if grading_scale and grading_scale.ranges:
                # Sort ranges by min_score descending to check highest grades first
                sorted_ranges = sorted(grading_scale.ranges, key=lambda x: x.get('min_score', 0), reverse=True)
                for grade_range in sorted_ranges:
                    min_score = grade_range.get('min_score', 0)
                    max_score = grade_range.get('max_score', 100)
                    if min_score <= self.score <= max_score:
                        return grade_range.get('grade', '')
        except (GradingScale.DoesNotExist, KeyError, TypeError, AttributeError):
            pass

        return None

    def save(self, *args, **kwargs):
        # Auto-calculate letter grade if not manually overridden and score is provided
        if not self.is_override and self.score is not None and not self.letter_grade:
            calculated_grade = self.calculate_letter_grade()
            if calculated_grade:
                self.letter_grade = calculated_grade

        super().save(*args, **kwargs)


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records', db_index=True)
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='attendance_records', db_index=True)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('student', 'class_section', 'date')

    def __str__(self):
        return f"{self.student.username} - {self.class_section.name} - {self.date}: {self.status}"


class UserApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, db_index=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_applications', db_index=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications', db_index=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} - {self.role} ({self.status})"

    def approve(self, reviewer):
        """Approve the application and create the user account"""
        if self.status != 'pending':
            return False

        # Create the user account
        user = User.objects.create_user(
            username=self.username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.role,
            school=self.school
        )

        # Update application status
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.save()

        return user

    def reject(self, reviewer, notes=''):
        """Reject the application"""
        if self.status != 'pending':
            return False

        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.save()

        return True



class ChangeLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    )

    model = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=100, db_index=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, db_index=True)
    data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.CASCADE, related_name='+')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.model} {self.object_id} {self.action} @ {self.timestamp.isoformat()}"


class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    category = models.CharField(max_length=100, blank=True, help_text="e.g., Technical, Account, Feature Request")
    
    # User who created the ticket
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tickets', db_index=True)
    # Staff member assigned to handle the ticket
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets', limit_choices_to={'role__in': ['admin', 'super_admin']}, db_index=True)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_tickets')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['school', 'status']),
        ]

    def __str__(self):
        return f"{self.title} - {self.status} ({self.created_by.username})"

    def save(self, *args, **kwargs):
        # Auto-set resolved_at when status changes to resolved
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = self.updated_at
        elif self.status != 'resolved':
            self.resolved_at = None
        super().save(*args, **kwargs)


class SchoolProfile(models.Model):
    """Extended school profile for white-label features and branding"""
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='profile')
    
    # Branding fields
    logo = models.ImageField(upload_to='school_logos/', null=True, blank=True, help_text="School logo for reports and branding")
    favicon = models.ImageField(upload_to='school_favicons/', null=True, blank=True, help_text="Favicon for the school's custom domain")
    
    # Color scheme
    primary_color = models.CharField(max_length=7, default='#667eea', help_text="Primary brand color (hex format, e.g., #667eea)")
    secondary_color = models.CharField(max_length=7, default='#764ba2', help_text="Secondary brand color (hex format)")
    accent_color = models.CharField(max_length=7, default='#28a745', help_text="Accent color for buttons and highlights")
    
    # Custom domain
    custom_domain = models.CharField(max_length=200, blank=True, help_text="Custom domain for the school (e.g., schoolname.reportcardapp.com)")
    
    # Contact information
    address = models.TextField(blank=True, help_text="School address")
    phone = models.CharField(max_length=20, blank=True, help_text="School contact phone")
    email = models.EmailField(blank=True, help_text="School contact email")
    website = models.URLField(blank=True, help_text="School website URL")
    
    # Report customization
    report_header = models.CharField(max_length=200, blank=True, help_text="Custom header text for report cards")
    report_footer = models.CharField(max_length=300, blank=True, help_text="Custom footer text for report cards")
    report_signature = models.CharField(max_length=100, blank=True, help_text="Principal/Head signature name")
    
    # Features toggle
    enable_analytics = models.BooleanField(default=True, help_text="Enable analytics dashboard for this school")
    enable_support_portal = models.BooleanField(default=True, help_text="Enable support ticket system")
    enable_custom_templates = models.BooleanField(default=True, help_text="Enable custom report templates")
    
    # Theme and appearance
    theme_mode = models.CharField(
        max_length=20,
        default='light',
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto'),
        ],
        help_text="Theme mode for reports and dashboard"
    )
    
    # Template selection
    default_report_template = models.CharField(
        max_length=50, 
        default='default', 
        choices=[
            ('default', 'Default Template'),
            ('modern', 'Modern Template'),
            ('classic', 'Classic Template'),
            ('minimal', 'Minimal Template'),
        ],
        help_text="Default template for report card generation"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Profile"
        verbose_name_plural = "School Profiles"

    def __str__(self):
        return f"{self.school.name} Profile"


# Report Template Models
class ReportTemplate(models.Model):
    """Customizable report card template"""
    
    TEMPLATE_TYPES = [
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('university', 'University'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField(max_length=200, help_text="Template name for identification")
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='report_templates')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, default='custom')
    
    # Layout Configuration
    header_logo = models.ImageField(upload_to='report_templates/logos/', blank=True, null=True)
    header_background_color = models.CharField(max_length=7, default='#ffffff', help_text="Hex color code")
    header_text_color = models.CharField(max_length=7, default='#000000', help_text="Hex color code")
    
    # Font Configuration
    font_family = models.CharField(max_length=100, default='Arial, sans-serif')
    font_size = models.PositiveIntegerField(default=12, help_text="Base font size in px")
    heading_font_size = models.PositiveIntegerField(default=16, help_text="Heading font size in px")
    
    # Layout Options
    include_student_photo = models.BooleanField(default=True)
    include_teacher_comments = models.BooleanField(default=True)
    include_principal_signature = models.BooleanField(default=True)
    include_grading_scale = models.BooleanField(default=True)
    include_attendance_summary = models.BooleanField(default=True)
    
    # Custom Fields
    custom_fields = models.JSONField(default=dict, blank=True, help_text="Additional custom fields")
    
    # Styling Options
    primary_color = models.CharField(max_length=7, default='#007bff', help_text="Primary brand color")
    secondary_color = models.CharField(max_length=7, default='#6c757d', help_text="Secondary brand color")
    border_style = models.CharField(max_length=20, default='solid', choices=[
        ('solid', 'Solid'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('none', 'None'),
    ])
    border_color = models.CharField(max_length=7, default='#dee2e6', help_text="Border color")
    
    # Content Configuration
    report_title = models.CharField(max_length=200, default='Report Card')
    grading_period_label = models.CharField(max_length=100, default='Grading Period')
    teacher_label = models.CharField(max_length=100, default='Class Teacher')
    principal_label = models.CharField(max_length=100, default='Principal')
    
    # Footer Configuration
    footer_text = models.TextField(blank=True, help_text="Custom footer text")
    show_school_stamp = models.BooleanField(default=True)
    show_contact_info = models.BooleanField(default=True)
    
    # Status and Metadata
    is_default = models.BooleanField(default=False, help_text="Set as default template for school")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Report Template"
        verbose_name_plural = "Report Templates"
        ordering = ['-is_default', 'name']
    
    def save(self, *args, **kwargs):
        # Ensure only one default template per school
        if self.is_default:
            ReportTemplate.objects.filter(school=self.school, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.school.name}"
    
    def get_template_config(self):
        """Return template configuration as dictionary"""
        return {
            'name': self.name,
            'template_type': self.template_type,
            'layout': {
                'header_logo': self.header_logo.url if self.header_logo else None,
                'header_background_color': self.header_background_color,
                'header_text_color': self.header_text_color,
                'include_student_photo': self.include_student_photo,
                'include_teacher_comments': self.include_teacher_comments,
                'include_principal_signature': self.include_principal_signature,
                'include_grading_scale': self.include_grading_scale,
                'include_attendance_summary': self.include_attendance_summary,
            },
            'styling': {
                'font_family': self.font_family,
                'font_size': self.font_size,
                'heading_font_size': self.heading_font_size,
                'primary_color': self.primary_color,
                'secondary_color': self.secondary_color,
                'border_style': self.border_style,
                'border_color': self.border_color,
            },
            'content': {
                'report_title': self.report_title,
                'grading_period_label': self.grading_period_label,
                'teacher_label': self.teacher_label,
                'principal_label': self.principal_label,
                'footer_text': self.footer_text,
                'show_school_stamp': self.show_school_stamp,
                'show_contact_info': self.show_contact_info,
            },
            'custom_fields': self.custom_fields,
        }


class TemplateSection(models.Model):
    """Configurable sections within a report template"""
    
    SECTION_TYPES = [
        ('header', 'Header'),
        ('student_info', 'Student Information'),
        ('academic_performance', 'Academic Performance'),
        ('attendance', 'Attendance'),
        ('teacher_comments', 'Teacher Comments'),
        ('principal_comments', 'Principal Comments'),
        ('footer', 'Footer'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    title = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    css_class = models.CharField(max_length=100, blank=True, help_text="Custom CSS class")
    
    # Section-specific configuration
    show_border = models.BooleanField(default=True)
    background_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    text_color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    
    # Content configuration
    content_template = models.TextField(blank=True, help_text="HTML template for this section")
    
    class Meta:
        ordering = ['order']
        unique_together = ['template', 'section_type']
    
    def __str__(self):
        return f"{self.template.name} - {self.get_section_type_display()}"


class TemplateField(models.Model):
    """Custom fields that can be added to report templates"""
    
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Yes/No'),
        ('select', 'Dropdown'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='template_fields')
    name = models.CharField(max_length=100, help_text="Field display name")
    field_key = models.CharField(max_length=50, help_text="Internal field key")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True, help_text="Options for select fields")
    default_value = models.CharField(max_length=200, blank=True, help_text="Default value")
    
    class Meta:
        ordering = ['order']
        unique_together = ['template', 'field_key']
    
    def __str__(self):
        return f"{self.template.name} - {self.name}"


class ReportTemplateUsage(models.Model):
    """Track template usage for analytics"""
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    report_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['template', 'school']
    
    def __str__(self):
        return f"{self.template.name} usage for {self.school.name}"


class ReportCard(models.Model):
    """Generated report card for a student in a specific grading period"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_cards', db_index=True)
    grading_period = models.ForeignKey(GradingPeriod, on_delete=models.CASCADE, related_name='report_cards', db_index=True)
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='report_cards', db_index=True)
    
    # Report card metadata
    academic_year = models.CharField(max_length=20, blank=True, help_text="Academic year (e.g., 2024/2025)")
    average_grade = models.FloatField(null=True, blank=True, help_text="Calculated average grade percentage")
    class_rank = models.PositiveIntegerField(null=True, blank=True, help_text="Student's rank in class")
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='published_report_cards', limit_choices_to={'role__in': ['admin', 'teacher']})
    
    # Generated content
    generated_data = models.JSONField(default=dict, blank=True, help_text="Generated report card data")
    pdf_file = models.FileField(upload_to='report_cards/pdfs/', null=True, blank=True, help_text="Generated PDF file")
    
    # Custom fields data
    custom_fields_data = models.JSONField(default=dict, blank=True, help_text="Custom field values for this report card")
    
    # Metadata
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_report_cards')
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['student', 'grading_period', 'template']
        indexes = [
            models.Index(fields=['student', 'grading_period']),
            models.Index(fields=['status', 'is_published']),
            models.Index(fields=['school', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.grading_period.name} - {self.template.name}"
    
    def save(self, *args, **kwargs):
        # Auto-set academic year from grading period if not provided
        if not self.academic_year and self.grading_period:
            self.academic_year = f"{self.grading_period.start_date.year}/{self.grading_period.end_date.year}"
        
        # Auto-set school from student if not provided
        if not self.school and self.student:
            self.school = self.student.school
        
        # Auto-set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = self.updated_at
            if not self.published_by:
                # Try to get the current user from the request context if available
                # This will be set by the view when publishing
                pass
        elif self.status != 'published':
            self.published_at = None
            self.published_by = None
        
        super().save(*args, **kwargs)
    
    def calculate_average_grade(self):
        """Calculate and update the average grade for this report card"""
        from django.db.models import Avg
        
        # Get all grades for this student in this grading period
        grades = Grade.objects.filter(
            student=self.student,
            grading_period=self.grading_period
        ).exclude(score__isnull=True)
        
        if grades.exists():
            avg_score = grades.aggregate(avg_score=Avg('score'))['avg_score']
            self.average_grade = round(avg_score, 2) if avg_score else None
            self.save(update_fields=['average_grade'])
            return self.average_grade
        else:
            self.average_grade = None
            self.save(update_fields=['average_grade'])
            return None
    
    def get_grades_data(self):
        """Get grades data for this report card"""
        return Grade.objects.filter(
            student=self.student,
            grading_period=self.grading_period
        ).select_related('subject').order_by('subject__name')
    
    def get_attendance_data(self):
        """Get attendance summary for this report card"""
        from django.db.models import Count, Q
        
        attendance_records = Attendance.objects.filter(
            student=self.student,
            date__gte=self.grading_period.start_date,
            date__lte=self.grading_period.end_date
        )
        
        total_days = attendance_records.count()
        present_days = attendance_records.filter(status='present').count()
        absent_days = attendance_records.filter(status='absent').count()
        late_days = attendance_records.filter(status='late').count()
        excused_days = attendance_records.filter(status='excused').count()
        
        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0
        
        return {
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': late_days,
            'excused_days': excused_days,
            'attendance_percentage': attendance_percentage
        }
    
    def get_class_rank(self):
        """Calculate student's rank in class for this grading period"""
        if not self.average_grade:
            return None
        
        # Get all students in the same class and grading period
        class_students = StudentEnrollment.objects.filter(
            class_section__enrollments__student=self.student,
            class_section__enrollments__grading_period=self.grading_period
        ).values_list('student_id', flat=True).distinct()
        
        # Get average grades for all students in the class
        class_averages = ReportCard.objects.filter(
            student_id__in=class_students,
            grading_period=self.grading_period,
            average_grade__isnull=False
        ).order_by('-average_grade')
        
        # Find rank
        for rank, report_card in enumerate(class_averages, 1):
            if report_card.student == self.student:
                self.class_rank = rank
                self.save(update_fields=['class_rank'])
                return rank
        
        return None
    
    def publish(self, published_by=None):
        """Publish this report card"""
        self.status = 'published'
        self.is_published = True
        self.published_at = timezone.now()
        self.published_by = published_by
        self.save()
        
        # Update template usage statistics
        usage, created = ReportTemplateUsage.objects.get_or_create(
            template=self.template,
            school=self.school
        )
        usage.report_count += 1
        usage.save()
    
    def unpublish(self):
        """Unpublish this report card"""
        self.status = 'draft'
        self.is_published = False
        self.published_at = None
        self.published_by = None
        self.save()
    
    def archive(self):
        """Archive this report card"""
        self.status = 'archived'
        self.is_published = False
        self.published_at = None
        self.published_by = None
        self.save()
    
    def get_generated_data(self):
        """Get the complete generated data for this report card"""
        if not self.generated_data:
            self.generate_data()
        
        return self.generated_data
    
    def generate_data(self):
        """Generate complete report card data"""
        from django.utils import timezone
        
        # Get student information
        student_info = {
            'id': self.student.id,
            'full_name': self.student.get_full_name(),
            'username': self.student.username,
            'email': self.student.email,
            'role': self.student.role,
            'school': self.student.school.name if self.student.school else '',
        }
        
        # Get class information
        enrollment = StudentEnrollment.objects.filter(
            student=self.student,
            class_section__enrollments__grading_period=self.grading_period
        ).first()
        
        class_info = {
            'name': enrollment.class_section.name if enrollment else '',
            'grade_level': enrollment.class_section.grade_level if enrollment else '',
            'teacher': enrollment.class_section.teacher.get_full_name() if enrollment and enrollment.class_section.teacher else '',
        }
        
        # Get grades data
        grades_data = []
        for grade in self.get_grades_data():
            grades_data.append({
                'subject': {
                    'name': grade.subject.name,
                    'code': grade.subject.code,
                },
                'score': grade.score,
                'letter_grade': grade.letter_grade,
                'comments': grade.comments,
                'grading_period': {
                    'name': grade.grading_period.name,
                    'start_date': grade.grading_period.start_date.strftime('%Y-%m-%d'),
                    'end_date': grade.grading_period.end_date.strftime('%Y-%m-%d'),
                }
            })
        
        # Get attendance data
        attendance_data = self.get_attendance_data()
        
        # Get template configuration
        template_config = self.template.get_template_config()
        
        # Generate complete data structure
        self.generated_data = {
            'report_card': {
                'id': self.id,
                'academic_year': self.academic_year,
                'average_grade': self.average_grade,
                'class_rank': self.class_rank,
                'status': self.status,
                'is_published': self.is_published,
                'published_at': self.published_at.isoformat() if self.published_at else None,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat(),
            },
            'student': student_info,
            'class': class_info,
            'grading_period': {
                'name': self.grading_period.name,
                'start_date': self.grading_period.start_date.strftime('%Y-%m-%d'),
                'end_date': self.grading_period.end_date.strftime('%Y-%m-%d'),
            },
            'grades': grades_data,
            'attendance': attendance_data,
            'template': template_config,
            'custom_fields': self.custom_fields_data,
            'generated_at': timezone.now().isoformat(),
        }
        
        self.save(update_fields=['generated_data'])
        return self.generated_data
