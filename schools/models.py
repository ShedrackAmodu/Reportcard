from django.contrib.auth.models import AbstractUser
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=255)
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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class ClassSection(models.Model):
    name = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50, blank=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_classes', limit_choices_to={'role': 'teacher'})
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        teacher_name = self.teacher.get_full_name() if self.teacher else "No Teacher"
        return f"{self.name} - {teacher_name} - {self.school.name}"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class GradingScale(models.Model):
    name = models.CharField(max_length=100)
    scale_type = models.CharField(max_length=50, default='letter')  # e.g., 'letter', 'percentage'
    ranges = models.JSONField(default=list)  # list of {'grade': 'A', 'min_score': 90, 'max_score': 100}
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} ({self.scale_type}) - {self.school.name}"


class StudentEnrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'class_section')

    def __str__(self):
        return f"{self.student.username} in {self.class_section.name}"


class GradingPeriod(models.Model):
    name = models.CharField(max_length=100)  # e.g., 'Q1', 'Semester 1', 'Term 1'
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date}) - {self.school.name}"


class Grade(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    grading_period = models.ForeignKey(GradingPeriod, on_delete=models.CASCADE, related_name='grades')
    score = models.FloatField(null=True, blank=True)  # Numeric score (0-100)
    letter_grade = models.CharField(max_length=10, blank=True)  # Calculated letter grade
    comments = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'grading_period')

    def __str__(self):
        return f"{self.student.username} - {self.subject.name} - {self.grading_period.name}: {self.letter_grade or self.score}"


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'class_section', 'date')

    def __str__(self):
        return f"{self.student.username} - {self.class_section.name} - {self.date}: {self.status}"
