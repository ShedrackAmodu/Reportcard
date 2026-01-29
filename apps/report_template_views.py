"""
Report Template Management Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods, require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
import json
import uuid
import os

from .models import (
    ReportTemplate, TemplateSection, TemplateField, ReportTemplateUsage, 
    School, User, Subject, ClassSection
)
from .forms import ReportTemplateForm, TemplateSectionForm, TemplateFieldForm
from .report_templates import create_default_template, get_school_template, duplicate_template
from authentication.permissions import IsSchoolAdmin, IsTeacherOrAdmin


@login_required
@require_http_methods(["GET"])
def template_list(request):
    """List all report templates for the school"""
    if not request.user.is_authenticated:
        return redirect('landing')
    
    # Check permissions - only admins and teachers can manage templates
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template management requires admin or teacher privileges.')
        return redirect('dashboard')

    school = request.user.school
    if not school:
        messages.error(request, 'No school assigned. Please contact your administrator.')
        return redirect('dashboard')

    templates = ReportTemplate.objects.filter(school=school).order_by('-created_at')
    
    # Get template usage statistics
    for template in templates:
        template.usage_count = ReportTemplateUsage.objects.filter(template=template).count()
        template.last_used = ReportTemplateUsage.objects.filter(
            template=template
        ).order_by('-created_at').first()

    context = {
        'templates': templates,
        'school': school,
        'title': 'Report Templates'
    }
    
    return render(request, 'report_templates/template_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def template_create(request):
    """Create a new report template"""
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template creation requires admin or teacher privileges.')
        return redirect('template_list')

    school = request.user.school
    if not school:
        messages.error(request, 'No school assigned. Please contact your administrator.')
        return redirect('template_list')

    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    template = form.save(commit=False)
                    template.school = school
                    template.created_by = request.user
                    template.save()
                    
                    # Create default sections if requested
                    if form.cleaned_data.get('create_default_sections'):
                        default_sections = [
                            {'section_type': 'header', 'title': 'School Header', 'order': 1},
                            {'section_type': 'student_info', 'title': 'Student Information', 'order': 2},
                            {'section_type': 'academic_performance', 'title': 'Academic Performance', 'order': 3},
                            {'section_type': 'attendance', 'title': 'Attendance Summary', 'order': 4},
                            {'section_type': 'teacher_comments', 'title': 'Teacher Comments', 'order': 5},
                            {'section_type': 'principal_comments', 'title': 'Principal Comments', 'order': 6},
                            {'section_type': 'footer', 'title': 'Footer', 'order': 7},
                        ]
                        
                        for section_data in default_sections:
                            TemplateSection.objects.create(
                                template=template,
                                **section_data
                            )
                    
                    messages.success(request, f'Template "{template.name}" created successfully.')
                    return redirect('template_list')
            except Exception as e:
                messages.error(request, f'Error creating template: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = ReportTemplateForm(request=request)

    context = {
        'form': form,
        'title': 'Create Report Template'
    }
    
    return render(request, 'report_templates/template_create.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def template_edit(request, template_id):
    """Edit an existing report template"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template editing requires admin or teacher privileges.')
        return redirect('template_list')
    
    if template.school != request.user.school:
        messages.error(request, 'Access denied. You can only edit templates from your school.')
        return redirect('template_list')

    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, request.FILES, instance=template, request=request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    template = form.save()
                    messages.success(request, f'Template "{template.name}" updated successfully.')
                    return redirect('template_list')
            except Exception as e:
                messages.error(request, f'Error updating template: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = ReportTemplateForm(instance=template, request=request)

    # Get template sections and fields for editing
    sections = template.sections.all().order_by('order')
    fields = template.custom_fields.all().order_by('order')

    context = {
        'form': form,
        'template': template,
        'sections': sections,
        'fields': fields,
        'title': f'Edit Template: {template.name}'
    }
    
    return render(request, 'report_templates/template_edit.html', context)


@login_required
@require_POST
def template_delete(request, template_id):
    """Delete a report template"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template deletion requires admin or teacher privileges.')
        return redirect('template_list')
    
    if template.school != request.user.school:
        messages.error(request, 'Access denied. You can only delete templates from your school.')
        return redirect('template_list')

    # Don't allow deletion of default templates
    if template.is_default:
        messages.error(request, 'Cannot delete the default template.')
        return redirect('template_list')

    # Check if template is in use
    usage_count = ReportTemplateUsage.objects.filter(template=template).count()
    if usage_count > 0:
        messages.warning(request, f'This template has been used {usage_count} times and will be archived instead of deleted.')
        template.is_active = False
        template.save()
    else:
        template.delete()
        messages.success(request, 'Template deleted successfully.')

    return redirect('template_list')


@login_required
@require_POST
def template_duplicate(request, template_id):
    """Duplicate a report template"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template duplication requires admin or teacher privileges.')
        return redirect('template_list')
    
    if template.school != request.user.school:
        messages.error(request, 'Access denied. You can only duplicate templates from your school.')
        return redirect('template_list')

    try:
        new_template = duplicate_template(template)
        messages.success(request, f'Template "{new_template.name}" duplicated successfully.')
        return redirect('template_edit', template_id=new_template.id)
    except Exception as e:
        messages.error(request, f'Error duplicating template: {str(e)}')
        return redirect('template_list')


@login_required
@require_http_methods(["GET"])
def template_preview(request, template_id):
    """Preview a report template"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template preview requires admin or teacher privileges.')
        return redirect('template_list')
    
    if template.school != request.user.school:
        messages.error(request, 'Access denied. You can only preview templates from your school.')
        return redirect('template_list')

    # Get template sections and fields
    sections = template.sections.filter(is_visible=True).order_by('order')
    fields = template.custom_fields.all().order_by('order')

    # Get sample data for preview
    sample_student = None
    sample_class = None
    sample_grades = []
    
    # Try to get sample data
    try:
        # Get a sample student from the school
        sample_student = User.objects.filter(
            role='student', 
            school=template.school
        ).first()
        
        if sample_student:
            # Get a sample class
            sample_class = ClassSection.objects.filter(
                school=template.school
            ).first()
            
            # Get sample grades
            sample_grades = []
            if sample_class:
                subjects = Subject.objects.filter(
                    class_sections=sample_class
                )[:3]  # Get first 3 subjects
                
                for subject in subjects:
                    sample_grades.append({
                        'subject': subject,
                        'score': 85.0,
                        'letter_grade': 'B',
                        'comments': 'Good performance'
                    })

    except Exception:
        pass  # Use empty sample data

    context = {
        'template': template,
        'sections': sections,
        'fields': fields,
        'sample_student': sample_student,
        'sample_class': sample_class,
        'sample_grades': sample_grades,
        'title': f'Preview Template: {template.name}'
    }
    
    return render(request, 'report_templates/template_preview.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def template_import(request):
    """Import a report template from JSON file"""
    if request.user.role not in ['admin', 'teacher']:
        messages.error(request, 'Access denied. Template import requires admin or teacher privileges.')
        return redirect('template_list')

    school = request.user.school
    if not school:
        messages.error(request, 'No school assigned. Please contact your administrator.')
        return redirect('template_list')

    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, 'Please select a JSON file to import.')
            return redirect('template_import')

        try:
            # Read and parse JSON file
            file_content = import_file.read().decode('utf-8')
            template_data = json.loads(file_content)

            # Validate required fields
            required_fields = ['name', 'template_type', 'sections', 'custom_fields']
            for field in required_fields:
                if field not in template_data:
                    messages.error(request, f'Invalid template file. Missing required field: {field}')
                    return redirect('template_import')

            with transaction.atomic():
                # Create template
                template = ReportTemplate.objects.create(
                    name=f"{template_data['name']} (Imported)",
                    school=school,
                    template_type=template_data['template_type'],
                    is_default=False,
                    header_background_color=template_data.get('header_background_color', '#ffffff'),
                    header_text_color=template_data.get('header_text_color', '#000000'),
                    font_family=template_data.get('font_family', 'Arial, sans-serif'),
                    font_size=template_data.get('font_size', 12),
                    heading_font_size=template_data.get('heading_font_size', 16),
                    primary_color=template_data.get('primary_color', '#007bff'),
                    secondary_color=template_data.get('secondary_color', '#6c757d'),
                    border_style=template_data.get('border_style', 'solid'),
                    border_color=template_data.get('border_color', '#dee2e6'),
                    report_title=template_data.get('report_title', 'Report Card'),
                    grading_period_label=template_data.get('grading_period_label', 'Grading Period'),
                    teacher_label=template_data.get('teacher_label', 'Class Teacher'),
                    principal_label=template_data.get('principal_label', 'Principal'),
                    footer_text=template_data.get('footer_text', f'Generated by {school.name} Report System'),
                    show_school_stamp=template_data.get('show_school_stamp', True),
                    show_contact_info=template_data.get('show_contact_info', True),
                    created_by=request.user,
                )

                # Create sections
                for section_data in template_data['sections']:
                    TemplateSection.objects.create(
                        template=template,
                        section_type=section_data['section_type'],
                        title=section_data['title'],
                        order=section_data['order'],
                        is_visible=section_data.get('is_visible', True),
                        css_class=section_data.get('css_class', ''),
                        show_border=section_data.get('show_border', True),
                        background_color=section_data.get('background_color', '#ffffff'),
                        text_color=section_data.get('text_color', '#000000'),
                        content_template=section_data.get('content_template', ''),
                    )

                # Create custom fields
                for field_data in template_data.get('custom_fields', []):
                    TemplateField.objects.create(
                        template=template,
                        name=field_data['name'],
                        field_key=field_data['field_key'],
                        field_type=field_data['field_type'],
                        order=field_data['order'],
                        is_required=field_data.get('is_required', False),
                        options=field_data.get('options', {}),
                        default_value=field_data.get('default_value', ''),
                    )

                messages.success(request, f'Template "{template.name}" imported successfully.')
                return redirect('template_list')

        except json.JSONDecodeError:
            messages.error(request, 'Invalid JSON file format.')
        except Exception as e:
            messages.error(request, f'Error importing template: {str(e)}')

    return render(request, 'report_templates/template_import.html', {
        'title': 'Import Report Template'
    })


# AJAX Views for dynamic template management

@login_required
@require_POST
def add_section(request, template_id):
    """Add a new section to a template via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    section_type = request.POST.get('section_type', 'custom')
    title = request.POST.get('title', 'New Section')
    
    # Calculate order
    max_order = template.sections.aggregate(max_order=Max('order'))['max_order'] or 0
    
    section = TemplateSection.objects.create(
        template=template,
        section_type=section_type,
        title=title,
        order=max_order + 1,
        is_visible=True
    )

    return JsonResponse({
        'id': section.id,
        'title': section.title,
        'section_type': section.section_type,
        'order': section.order
    })


@login_required
@require_POST
def update_section(request, template_id, section_id):
    """Update a template section via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    section = get_object_or_404(TemplateSection, id=section_id, template=template)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    form = TemplateSectionForm(request.POST, instance=section)
    if form.is_valid():
        section = form.save()
        return JsonResponse({
            'success': True,
            'title': section.title,
            'section_type': section.section_type,
            'is_visible': section.is_visible
        })
    else:
        return JsonResponse({'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_section(request, template_id, section_id):
    """Delete a template section via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    section = get_object_or_404(TemplateSection, id=section_id, template=template)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    section.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def add_field(request, template_id):
    """Add a new custom field to a template via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    name = request.POST.get('name', 'New Field')
    field_key = request.POST.get('field_key', f'field_{uuid.uuid4().hex[:8]}')
    field_type = request.POST.get('field_type', 'text')
    
    # Calculate order
    max_order = template.custom_fields.aggregate(max_order=Max('order'))['max_order'] or 0
    
    field = TemplateField.objects.create(
        template=template,
        name=name,
        field_key=field_key,
        field_type=field_type,
        order=max_order + 1,
        is_required=False
    )

    return JsonResponse({
        'id': field.id,
        'name': field.name,
        'field_key': field.field_key,
        'field_type': field.field_type,
        'order': field.order
    })


@login_required
@require_POST
def update_field(request, template_id, field_id):
    """Update a custom field via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    field = get_object_or_404(TemplateField, id=field_id, template=template)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    form = TemplateFieldForm(request.POST, instance=field)
    if form.is_valid():
        field = form.save()
        return JsonResponse({
            'success': True,
            'name': field.name,
            'field_type': field.field_type,
            'is_required': field.is_required
        })
    else:
        return JsonResponse({'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_field(request, template_id, field_id):
    """Delete a custom field via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    field = get_object_or_404(TemplateField, id=field_id, template=template)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    field.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def reorder_sections(request, template_id):
    """Reorder template sections via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    section_order = request.POST.getlist('section_order[]')
    
    for index, section_id in enumerate(section_order):
        try:
            section = TemplateSection.objects.get(id=section_id, template=template)
            section.order = index + 1
            section.save()
        except TemplateSection.DoesNotExist:
            continue

    return JsonResponse({'success': True})


@login_required
@require_POST
def reorder_fields(request, template_id):
    """Reorder custom fields via AJAX"""
    template = get_object_or_404(ReportTemplate, id=template_id)
    
    if request.user.role not in ['admin', 'teacher'] or template.school != request.user.school:
        return JsonResponse({'error': 'Access denied'}, status=403)

    field_order = request.POST.getlist('field_order[]')
    
    for index, field_id in enumerate(field_order):
        try:
            field = TemplateField.objects.get(id=field_id, template=template)
            field.order = index + 1
            field.save()
        except TemplateField.DoesNotExist:
            continue

    return JsonResponse({'success': True})