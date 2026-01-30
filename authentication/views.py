from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.http import JsonResponse

from .forms import RegistrationForm


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegistrationForm()

    return render(request, 'auth/register.html', {
        'form': form,
        'title': 'Register'
    })


@require_http_methods(["GET", "POST"])
@never_cache
def logout_view(request):
    """Log out the user via GET or POST and redirect to landing."""
    # Clear Django session
    logout(request)
    
    # Create a response that redirects to landing
    response = redirect('landing')
    
    # Clear all cache headers to prevent caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # Clear cookies that might be used for authentication
    response.delete_cookie('sessionid')
    response.delete_cookie('csrftoken')
    response.delete_cookie('auth_token')
    response.delete_cookie('authtoken')
    
    return response
