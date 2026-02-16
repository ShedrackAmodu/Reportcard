from model_utils.models import TimeStampedModel

from django.db import models
from django.conf import settings
from django.urls import reverse

from apps.students.models import Student
from apps.academics.models import Subject, Semester, Department


class Exam(TimeStampedModel):
    EXAM_CHOICES = (
        ('m', 'Mid Term'),
        ('f', 'Final')
    )
    exam_name = models.CharField(
        max_length=1,
        choices=EXAM_CHOICES
    )
    exam_date = models.DateTimeField()

    def __str__(self):
        return f'{self.get_exam_name_display()} - \
            {self.exam_date.year}'


class Result(TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='results'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE,
        blank=True, null=True
    )
    practical_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )
    theory_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )
    total_marks = models.SmallIntegerField(
        blank=True,
        null=True
    )

    class Meta:
        unique_together =  ('student', 'semester', 'subject')

    def __str__(self):
        return f'{self.student} | {self.subject} | {self.total_marks}'
    
    def save(self, *args, **kwargs):
        # Preserve existing behavior but correctly handle zero scores.
        theory_marks = self.theory_marks if self.theory_marks is not None else None
        practical_marks = self.practical_marks if self.practical_marks is not None else None
        if theory_marks is None and practical_marks is None:
            self.total_marks = None
        else:
            self.total_marks = (theory_marks or 0) + (practical_marks or 0)
        super().save(*args, **kwargs)

    def get_grade_profile(self):
        """
        Return grade metadata for common Nigerian school report formats.
        Schools can override with RESULT_GRADE_SCALE in Django settings using:
        (min_mark, max_mark, grade, point, remark)
        """
        score = self.total_marks if self.total_marks is not None else 0
        default_scale = (
            (75, 100, 'A1', 4.0, 'Excellent'),
            (70, 74, 'B2', 3.6, 'Very Good'),
            (65, 69, 'B3', 3.2, 'Good'),
            (60, 64, 'C4', 2.8, 'Credit'),
            (55, 59, 'C5', 2.4, 'Credit'),
            (50, 54, 'C6', 2.0, 'Credit'),
            (45, 49, 'D7', 1.6, 'Pass'),
            (40, 44, 'E8', 1.0, 'Pass'),
            (0, 39, 'F9', 0.0, 'Fail'),
        )
        grade_scale = getattr(settings, 'RESULT_GRADE_SCALE', default_scale)
        for minimum, maximum, grade, point, remark in grade_scale:
            if minimum <= score <= maximum:
                return {
                    'grade': grade,
                    'point': point,
                    'remark': remark,
                }
        return {
            'grade': 'N/A',
            'point': 0.0,
            'remark': 'Not Graded',
        }

    @property
    def grade(self):
        return self.get_grade_profile()['grade']

    @property
    def grade_point(self):
        return self.get_grade_profile()['point']

    @property
    def remark(self):
        return self.get_grade_profile()['remark']


class SubjectGroup(TimeStampedModel):
    """ Keep track of group of subjects that belongs to a
    department, semester
    """
    department = models.ForeignKey(
        Department,
        related_name='subjects',
        on_delete=models.DO_NOTHING
    )
    semester = models.ForeignKey(
        Semester,
        related_name='subjects',
        on_delete=models.CASCADE
    )
    subjects = models.ManyToManyField(Subject, blank=True)

    def __str__(self):
        return f'{self.department} - {self.semester}'
    
    def get_subjects(self):
        return " | ".join([str(sg) for sg in self.subjects.all()])

    def create_resource(self):
        return reverse('result:create_subject_group')


class Attendance(TimeStampedModel):
    """ Track student attendance for specific subjects and dates """
    ATTENDANCE_STATUS_CHOICES = (
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Late'),
        ('E', 'Excused'),
    )
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE
    )
    date = models.DateField()
    status = models.CharField(
        max_length=1,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='P'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('student', 'subject', 'semester', 'date')
        ordering = ['-date', 'student__admission_student__name']

    def __str__(self):
        return f'{self.student} - {self.subject} - {self.date} - {self.get_status_display()}'

    def save(self, *args, **kwargs):
        # Set created_by to the current user if available
        if hasattr(self, '_current_user') and self._current_user:
            self.created_by = self._current_user
        super().save(*args, **kwargs)