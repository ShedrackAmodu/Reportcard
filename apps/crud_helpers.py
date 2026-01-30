"""
Generic CRUD view helpers to reduce boilerplate for list/create/update/delete views.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def check_admin_permission(view_func):
    """Decorator to check if user is admin or super_admin"""
    def wrapper(request, *args, **kwargs):
        if request.user.role not in ['super_admin', 'admin']:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return login_required(wrapper)


def check_school_access(obj, user):
    """Check if user has access to object based on school"""
    if user.role == 'super_admin':
        return True
    if user.role == 'admin' and obj.school == user.school:
        return True
    return False


class GenericCRUDMixin:
    """Mixin to reduce boilerplate for standard CRUD operations"""
    
    model = None
    form_class = None
    template_name_list = None
    template_name_form = None
    template_name_delete = None
    permission_required = 'admin'  # 'admin', 'super_admin', or None
    
    def get_permission_denied_response(self, request):
        """Handle permission denied"""
        messages.error(request, 'Access denied.')
        return redirect(f'{self.model.__name__.lower()}_list')
    
    def check_school_access(self, request, obj):
        """Override in subclass for custom access checks"""
        return check_school_access(obj, request.user)
    
    def get_list_queryset(self, request):
        """Override to customize list queryset"""
        queryset = self.model.objects.all()
        if request.user.role == 'admin' and hasattr(self.model, 'school'):
            queryset = queryset.filter(school=request.user.school)
        return queryset.order_by('school', 'name') if hasattr(self.model, 'school') else queryset
    
    def list_view(self, request):
        """Generic list view"""
        if request.user.role not in [self.permission_required, 'super_admin']:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
        
        objects = self.get_list_queryset(request)
        return render(request, self.template_name_list, {
            'objects': objects,
            'title': f'Manage {self.model.__name__}s'
        })
    
    def create_view(self, request):
        """Generic create view"""
        if request.user.role not in [self.permission_required, 'super_admin']:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
        
        if request.method == 'POST':
            form = self.form_class(request.POST, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, f'{self.model.__name__} created successfully.')
                return redirect(f'{self.model.__name__.lower()}_list')
        else:
            form = self.form_class(request=request)
        
        return render(request, self.template_name_form, {
            'form': form,
            'title': f'Create {self.model.__name__}'
        })
    
    def update_view(self, request, pk):
        """Generic update view"""
        if request.user.role not in [self.permission_required, 'super_admin']:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
        
        obj = get_object_or_404(self.model, pk=pk)
        
        if not self.check_school_access(request, obj):
            messages.error(request, 'Access denied.')
            return redirect(f'{self.model.__name__.lower()}_list')
        
        if request.method == 'POST':
            form = self.form_class(request.POST, instance=obj, request=request)
            if form.is_valid():
                form.save()
                messages.success(request, f'{self.model.__name__} updated successfully.')
                return redirect(f'{self.model.__name__.lower()}_list')
        else:
            form = self.form_class(instance=obj, request=request)
        
        return render(request, self.template_name_form, {
            'form': form,
            'object': obj,
            'title': f'Edit {self.model.__name__}'
        })
    
    def delete_view(self, request, pk):
        """Generic delete view"""
        if request.user.role not in [self.permission_required, 'super_admin']:
            messages.error(request, 'Access denied.')
            return redirect('dashboard')
        
        obj = get_object_or_404(self.model, pk=pk)
        
        if not self.check_school_access(request, obj):
            messages.error(request, 'Access denied.')
            return redirect(f'{self.model.__name__.lower()}_list')
        
        if request.method == 'POST':
            obj.delete()
            messages.success(request, f'{self.model.__name__} deleted successfully.')
            return redirect(f'{self.model.__name__.lower()}_list')
        
        return render(request, self.template_name_delete, {
            'object': obj,
            'title': f'Delete {self.model.__name__}'
        })
