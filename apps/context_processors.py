from django.conf import settings
from .models import SchoolProfile

def school_context(request):
    """Context processor to provide school information to templates"""
    context = {}
    
    # Get the current school from the request
    school = getattr(request, 'school', None)
    user = getattr(request, 'user', None)
    
    if school and user and user.is_authenticated:
        try:
            # Get school profile
            school_profile = SchoolProfile.objects.get(school=school)
            context['school_profile'] = school_profile
            context['current_school'] = school
        except SchoolProfile.DoesNotExist:
            context['school_profile'] = None
            context['current_school'] = school
    else:
        context['school_profile'] = None
        context['current_school'] = None
    
    return context

def school_branding(request):
    """Context processor to provide school branding information to templates"""
    context = {}
    
    # Get the current school from the request
    school = getattr(request, 'school', None)
    user = getattr(request, 'user', None)
    
    if school and user and user.is_authenticated:
        try:
            # Get school profile
            school_profile = SchoolProfile.objects.get(school=school)
            context['school_profile'] = school_profile
            
            # Add CSS variables for theming
            context['branding_css'] = f"""
                :root {{
                    --primary-color: {school_profile.primary_color};
                    --secondary-color: {school_profile.secondary_color};
                    --accent-color: {school_profile.accent_color};
                    --primary-rgb: {hex_to_rgb(school_profile.primary_color)};
                    --secondary-rgb: {hex_to_rgb(school_profile.secondary_color)};
                    --accent-rgb: {hex_to_rgb(school_profile.accent_color)};
                }}
            """
            
            # Add theme mode class
            context['theme_class'] = f"theme-{school_profile.theme_mode}"
            
        except SchoolProfile.DoesNotExist:
            # Use default colors if no profile exists
            context['branding_css'] = """
                :root {
                    --primary-color: #667eea;
                    --secondary-color: #764ba2;
                    --accent-color: #28a745;
                    --primary-rgb: 102, 126, 234;
                    --secondary-rgb: 118, 75, 162;
                    --accent-rgb: 40, 167, 69;
                }
            """
            context['theme_class'] = "theme-light"
            context['school_profile'] = None
    else:
        # Default colors for non-authenticated users or when no school is set
        context['branding_css'] = """
            :root {
                --primary-color: #667eea;
                --secondary-color: #764ba2;
                --accent-color: #28a745;
                --primary-rgb: 102, 126, 234;
                --secondary-rgb: 118, 75, 162;
                --accent-rgb: 40, 167, 69;
            }
        """
        context['theme_class'] = "theme-light"
        context['school_profile'] = None
    
    return context

def hex_to_rgb(hex_color):
    """Convert hex color to RGB values"""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    
    if len(hex_color) == 3:
        hex_color = hex_color * 2
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    except (ValueError, IndexError):
        return "102, 126, 234"  # Default to primary color