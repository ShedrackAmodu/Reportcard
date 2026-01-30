"""
Base form classes to eliminate redundancy in form initialization.
Consolidates common patterns like school filtering and permission handling.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import School, User, ClassSection, Subject


class BaseSchoolForm(forms.ModelForm):
    """Base form for models with school relationships"""
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self._filter_school_field()
    
    def _filter_school_field(self):
        """Filter school field based on user role"""
        if not self.request:
            return
        
        if 'school' in self.fields:
            if self.request.user.role == 'super_admin':
                pass  # Can see all schools
            else:
                self.fields['school'].queryset = School.objects.filter(
                    id=self.request.user.school.id
                )
                if not self.instance.pk:
                    self.fields['school'].initial = self.request.user.school
                    self.fields['school'].widget = forms.HiddenInput()


class BaseTeacherFilterForm(BaseSchoolForm):
    """Base form for models that reference teachers"""
    
    def _filter_school_field(self):
        super()._filter_school_field()
        
        if not self.request or 'teacher' not in self.fields:
            return
        
        if self.request.user.role == 'super_admin':
            pass
        else:
            school = self.request.user.school
            self.fields['teacher'].queryset = User.objects.filter(
                school=school, role='teacher'
            )


class BaseStudentFilterForm(BaseSchoolForm):
    """Base form for models that reference students"""
    
    def _filter_school_field(self):
        super()._filter_school_field()
        
        if not self.request or 'student' not in self.fields:
            return
        
        if self.request.user.role == 'super_admin':
            pass
        else:
            school = self.request.user.school
            self.fields['student'].queryset = User.objects.filter(
                school=school, role='student'
            )


class BaseMultiSchoolFilterForm(BaseSchoolForm):
    """Base form for models with multiple school-related fields"""
    
    def _filter_school_field(self):
        super()._filter_school_field()
        
        if not self.request:
            return
        
        school = self.request.user.school if self.request.user.role != 'super_admin' else None
        
        # Filter related fields based on school
        if 'subject' in self.fields and school:
            self.fields['subject'].queryset = Subject.objects.filter(school=school)
        
        if 'class_section' in self.fields and school:
            self.fields['class_section'].queryset = ClassSection.objects.filter(school=school)
