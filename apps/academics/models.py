from django.db import models
from django.conf import settings

class ClassSection(models.Model):
	name = models.CharField(max_length=200)
	grade_level = models.CharField(max_length=50, blank=True)
	school = models.ForeignKey("apps.schools.School", on_delete=models.CASCADE, related_name="class_sections")

	def __str__(self):
		return f"{self.name} ({self.grade_level})"

class Subject(models.Model):
	name = models.CharField(max_length=200)
	code = models.CharField(max_length=50, blank=True)
	description = models.TextField(blank=True)
	school = models.ForeignKey("apps.schools.School", on_delete=models.CASCADE, related_name="subjects")

	def __str__(self):
		return self.name

class GradingScale(models.Model):
	name = models.CharField(max_length=200)
	scale_type = models.CharField(max_length=50, blank=True)
	ranges = models.JSONField(default=list, blank=True)
	school = models.ForeignKey("apps.schools.School", on_delete=models.CASCADE, related_name="grading_scales")

	def __str__(self):
		return self.name

class StudentEnrollment(models.Model):
	student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
	class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name="enrollments")
	enrollment_date = models.DateField(auto_now_add=True)
	school = models.ForeignKey("apps.schools.School", on_delete=models.CASCADE, related_name="enrollments")

	def __str__(self):
		return f"{self.student} in {self.class_section}"

class GradingPeriod(models.Model):
	name = models.CharField(max_length=200)
	kind = models.CharField(max_length=50, blank=True)  # quarter/semester/term
	start_date = models.DateField()
	end_date = models.DateField()
	school = models.ForeignKey("apps.schools.School", on_delete=models.CASCADE, related_name="grading_periods")

	def __str__(self):
		return self.name