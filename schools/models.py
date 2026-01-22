from django.contrib.auth.models import AbstractUser
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    theme = models.JSONField(default=dict)  # School theme configuration
    report_template = models.JSONField(default=dict)  # Report card template
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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


class ClassSection(models.Model):
    name = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classes', limit_choices_to={'role': 'teacher'}, db_index=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        teacher_name = self.teacher.get_full_name() if self.teacher else "No Teacher"
        return f"{self.name} - {teacher_name} - {self.school.name}"


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
