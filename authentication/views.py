"""
Authentication views for login, logout, registration, and token management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.models import User, School, UserApplication


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user role in token claims.
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['role'] = user.role
        token['school_id'] = user.school.id if user.school else None
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view using CustomTokenObtainPairSerializer.
    """
    serializer_class = CustomTokenObtainPairSerializer


def login_view(request):
    """
    Handle user login with multi-tenant support.
    - Authenticated users are redirected to dashboard
    - Displays available schools for selection
    - Supports 'next' parameter for post-login redirect
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    schools = School.objects.all()

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        school_id = request.POST.get('school')
        
        if form.is_valid():
            user = form.get_user()
            
            # Ensure Django superusers have the 'super_admin' role
            if user.is_superuser and user.role != 'super_admin':
                user.role = 'super_admin'
                user.save()
            
            # For multi-tenancy, set school in session if selected
            # Only require school selection for non-super_admin users
            if user.role != 'super_admin' and school_id:
                try:
                    selected_school = School.objects.get(id=school_id)
                    request.session['school_id'] = selected_school.id
                except School.DoesNotExist:
                    pass
            elif user.role == 'super_admin':
                # Super admins don't need school selection, clear any existing school context
                request.session.pop('school_id', None)
            
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Check for 'next' parameter to redirect to intended page
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form, 'schools': schools})


@login_required(login_url='login')
def logout_view(request):
    """
    Handle user logout.
    - Clears all session data
    - Logs out the user
    - Redirects to landing page with cache control headers
    """
    # Clear all session data
    request.session.flush()
    
    # Logout the user
    logout(request)
    
    # Add success message
    messages.info(request, 'You have been logged out successfully.')
    
    # Redirect to landing page with cache control headers
    response = redirect('landing')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


def register_view(request):
    """
    Handle user registration.
    - Students can register directly
    - Teachers/Admins must submit applications for approval
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    from authentication.forms import UserApplicationForm
    
    schools = School.objects.all()

    if request.method == 'POST':
        form = UserApplicationForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data['role']
            
            # Students can register directly
            if role == 'student':
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    role=role,
                    school=form.cleaned_data['school']
                )
                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')
            else:
                # Admin/Teacher applications need approval
                application = form.save(commit=False)
                application.submitted_by = request.user if request.user.is_authenticated else None
                application.save()
                messages.success(
                    request, 
                    f'Application submitted for {role} role. It will be reviewed by the appropriate administrator.'
                )
                return redirect('landing')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserApplicationForm()

    return render(request, 'auth/register.html', {
        'form': form,
        'schools': schools,
        'title': 'Register for ReportCardApp'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_token_view(request):
    """
    API endpoint to verify if the provided token is valid.
    Returns user information and role if token is valid.
    """
    return Response({
        'user_id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'role': request.user.role,
        'school_id': request.user.school.id if request.user.school else None,
        'is_authenticated': True
    })
