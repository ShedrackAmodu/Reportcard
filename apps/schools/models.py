from django.db import models

class School(models.Model):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=100, unique=True)
	theme = models.JSONField(default=dict, blank=True)
	settings = models.JSONField(default=dict, blank=True)

	def __str__(self):
		return self.name