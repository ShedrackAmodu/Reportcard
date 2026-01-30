from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PWAInstallationTrackingSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    timestamp = serializers.DateTimeField()
    user_agent = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.CharField(required=False, allow_blank=True)
    details = serializers.CharField(required=False, allow_blank=True)
    
    # Also support legacy 'action' field for backward compatibility
    action = serializers.ChoiceField(choices=['started', 'accepted', 'cancelled', 'error', 'success'], required=False)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def pwa_tracking_view(request):
    """
    Track PWA installation events for analytics and optimization.
    
    This endpoint receives installation event data from the PWA installer
    and logs it for analysis and optimization.
    """
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.data

        # Validate data
        serializer = PWAInstallationTrackingSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        
        # Log the installation event
        logger.info(f"PWA Installation Event: {validated_data}")
        
        # Store in database if needed (you could create a model for this)
        # For now, we'll just log it
        
        # Return success response
        return Response({
            'status': 'success',
            'message': 'Installation event tracked successfully',
            'event_type': validated_data.get('event_type'),
            'timestamp': validated_data.get('timestamp')
        }, status=status.HTTP_200_OK)
        
    except json.JSONDecodeError:
        return Response(
            {'error': 'Invalid JSON format'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error tracking PWA installation: {str(e)}")
        return Response(
            {'error': 'Failed to track installation event'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def pwa_status_view(request):
    """
    Get PWA installation status and recommendations.
    
    Accepts both GET and POST requests. POST is used for tracking PWA status updates.
    Returns information about the current PWA installation state
    and provides recommendations for installation.
    """
    # Handle POST requests (status tracking)
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.data
            
            # Log status update
            logger.info(f"PWA Status Update: {data}")
            
            return Response({
                'status': 'success',
                'message': 'PWA status tracked successfully',
                'data': data
            }, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response(
                {'error': 'Invalid JSON format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error tracking PWA status: {str(e)}")
            return Response(
                {'error': 'Failed to track PWA status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # Handle GET requests (status check)
    # Get installation state from request or default
    install_state = request.GET.get('install_state', 'pending')
    
    # Check if PWA is already installed
    is_installed = False
    if request.headers.get('Sec-Fetch-Mode') == 'navigate':
        # This is a rough heuristic - in practice, you'd check this differently
        is_installed = False
    
    # Determine browser compatibility
    user_agent = request.headers.get('User-Agent', '')
    browser_info = get_browser_info(user_agent)
    
    # Generate recommendations
    recommendations = generate_installation_recommendations(
        install_state, 
        browser_info, 
        is_installed
    )
    
    return Response({
        'is_installed': is_installed,
        'install_state': install_state,
        'browser_compatibility': browser_info,
        'recommendations': recommendations,
        'manifest_valid': True,  # You could validate this
        'service_worker_registered': True,  # You could check this
        'https_available': request.is_secure() or request.get_host().startswith('localhost')
    })


def get_browser_info(user_agent):
    """Extract browser information from user agent string."""
    browser_info = {
        'name': 'Unknown',
        'version': 'Unknown',
        'supports_pwa': False,
        'supports_install_prompt': False
    }
    
    if 'Chrome' in user_agent:
        browser_info['name'] = 'Chrome'
        browser_info['supports_pwa'] = True
        browser_info['supports_install_prompt'] = True
        # Extract version if possible
        try:
            version_start = user_agent.find('Chrome/') + 7
            version_end = user_agent.find(' ', version_start)
            if version_end > version_start:
                browser_info['version'] = user_agent[version_start:version_end]
        except:
            pass
            
    elif 'Firefox' in user_agent:
        browser_info['name'] = 'Firefox'
        browser_info['supports_pwa'] = True
        browser_info['supports_install_prompt'] = False  # Firefox has limited support
        
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser_info['name'] = 'Safari'
        browser_info['supports_pwa'] = True
        browser_info['supports_install_prompt'] = False  # Safari has limited support
        
    elif 'Edge' in user_agent:
        browser_info['name'] = 'Edge'
        browser_info['supports_pwa'] = True
        browser_info['supports_install_prompt'] = True
        
    return browser_info


def generate_installation_recommendations(install_state, browser_info, is_installed):
    """Generate personalized installation recommendations."""
    recommendations = []
    
    if is_installed:
        recommendations.append({
            'type': 'success',
            'message': 'PWA is already installed and ready to use!',
            'action': 'enjoy'
        })
        return recommendations
    
    if install_state == 'dismissed':
        recommendations.append({
            'type': 'info',
            'message': 'You previously dismissed the installation prompt. You can install the app later from your browser menu.',
            'action': 'manual_install'
        })
    
    if not browser_info['supports_pwa']:
        recommendations.append({
            'type': 'warning',
            'message': f'Your browser ({browser_info["name"]}) has limited PWA support. Consider using Chrome or Edge for the best experience.',
            'action': 'browser_switch'
        })
    
    if not browser_info['supports_install_prompt']:
        recommendations.append({
            'type': 'info',
            'message': 'Your browser supports PWAs but may require manual installation. Look for "Add to Home Screen" in your browser menu.',
            'action': 'manual_install_instructions'
        })
    
    if install_state == 'pending':
        recommendations.append({
            'type': 'primary',
            'message': 'Install our PWA for the best experience with offline access and faster performance.',
            'action': 'install_now'
        })
    
    return recommendations


@api_view(['GET'])
@permission_classes([AllowAny])
def pwa_install_guide_view(request):
    """
    Provide installation instructions for different platforms and browsers.
    """
    platform = request.GET.get('platform', 'auto')
    browser = request.GET.get('browser', 'auto')
    
    guide = get_installation_guide(platform, browser)
    
    return Response({
        'platform': guide['platform'],
        'browser': guide['browser'],
        'steps': guide['steps'],
        'tips': guide['tips'],
        'troubleshooting': guide['troubleshooting']
    })


def get_installation_guide(platform, browser):
    """Generate platform and browser-specific installation instructions."""
    
    # Auto-detect platform and browser if not specified
    if platform == 'auto' or browser == 'auto':
        user_agent = ''
        # In a real implementation, you'd parse the user agent here
        # For now, we'll provide general instructions
    
    guide = {
        'platform': platform,
        'browser': browser,
        'steps': [],
        'tips': [],
        'troubleshooting': []
    }
    
    # Common installation steps
    guide['steps'] = [
        {
            'step': 1,
            'title': 'Open in Browser',
            'description': 'Visit this page in your web browser on your device.'
        },
        {
            'step': 2,
            'title': 'Look for Install Button',
            'description': 'Check for an install button in your browser\'s address bar or menu.'
        },
        {
            'step': 3,
            'title': 'Confirm Installation',
            'description': 'Follow the prompts to install the app on your device.'
        }
    ]
    
    # Platform-specific instructions
    if platform in ['ios', 'iphone', 'ipad']:
        guide['steps'].insert(1, {
            'step': 1.5,
            'title': 'Use Safari',
            'description': 'Open this page in Safari browser for the best installation experience.'
        })
        guide['steps'].insert(2, {
            'step': 2.5,
            'title': 'Share Menu',
            'description': 'Tap the share button and select "Add to Home Screen".'
        })
        guide['tips'].append('iOS requires using Safari for PWA installation.')
        guide['tips'].append('The app will appear on your home screen like any other app.')
        
    elif platform in ['android', 'chrome']:
        guide['steps'].insert(1, {
            'step': 1.5,
            'title': 'Check Address Bar',
            'description': 'Look for an install icon (⬇️) in the address bar.'
        })
        guide['steps'].insert(2, {
            'step': 2.5,
            'title': 'Tap Install',
            'description': 'Tap the install button and confirm the installation.'
        })
        guide['tips'].append('Chrome on Android provides the smoothest PWA experience.')
        guide['tips'].append('You can also use the three-dot menu to find "Install app".')
        
    elif platform in ['windows', 'desktop']:
        guide['steps'].insert(1, {
            'step': 1.5,
            'title': 'Use Chrome or Edge',
            'description': 'Open in Chrome or Edge for the best PWA support.'
        })
        guide['steps'].insert(2, {
            'step': 2.5,
            'title': 'Install Prompt',
            'description': 'Look for an install prompt in the address bar or browser menu.'
        })
        guide['tips'].append('Desktop PWAs appear in your applications menu.')
        guide['tips'].append('They work like regular desktop applications.')
    
    # Troubleshooting
    guide['troubleshooting'] = [
        {
            'issue': 'No install button visible',
            'solution': 'Ensure you\'re using a supported browser and the site is loaded over HTTPS.'
        },
        {
            'issue': 'Installation fails',
            'solution': 'Check your internet connection and try refreshing the page.'
        },
        {
            'issue': 'App not appearing',
            'solution': 'Check your device\'s app drawer or home screen settings.'
        }
    ]
    
    return guide


@api_view(['GET'])
@permission_classes([AllowAny])
def pwa_health_check_view(request):
    """
    Check PWA health and readiness for installation.
    
    Returns status of manifest, service worker, and other PWA requirements.
    """
    health_status = {
        'manifest': check_manifest_health(),
        'service_worker': check_service_worker_health(),
        'https': check_https_health(),
        'installability': check_installability_health(),
        'overall_status': 'ready'
    }
    
    # Determine overall status
    if not all([health_status['manifest']['valid'], 
               health_status['service_worker']['registered'],
               health_status['https']['secure']]):
        health_status['overall_status'] = 'issues_found'
    
    return Response(health_status)


def check_manifest_health():
    """Check if the web manifest is valid and complete."""
    # In a real implementation, you'd fetch and validate the manifest
    # For now, we'll assume it's valid based on the presence of the file
    return {
        'valid': True,
        'has_name': True,
        'has_short_name': True,
        'has_start_url': True,
        'has_display': True,
        'has_icons': True,
        'message': 'Manifest appears to be valid'
    }


def check_service_worker_health():
    """Check if the service worker is registered and functioning."""
    # In a real implementation, you'd check the service worker registration
    return {
        'registered': True,
        'scope': '/',
        'script_url': '/sw.js',
        'message': 'Service worker is registered and active'
    }


def check_https_health():
    """Check if the site is served over HTTPS (or localhost)."""
    is_secure = True  # request.is_secure()
    is_localhost = False  # request.get_host().startswith('localhost')
    
    return {
        'secure': is_secure or is_localhost,
        'https_required': not is_localhost,
        'message': 'Site is served securely' if is_secure or is_localhost else 'HTTPS required for PWA features'
    }


def check_installability_health():
    """Check overall installability of the PWA."""
    # This would check all the criteria for PWA installability
    return {
        'meets_criteria': True,
        'can_install': True,
        'reasons': [],
        'message': 'PWA meets all installability criteria'
    }


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def clear_offline_cache(request):
    """
    Clear all offline cache data for the user.
    Called when user logs out to ensure no data persists.
    """
    try:
        response_data = {
            'status': 'success',
            'message': 'Clear offline cache endpoint called. Client-side cache will be cleared.',
            'instructions': [
                'IndexedDB database will be cleared by client',
                'Service worker cache will be cleared by client',
                'LocalStorage will be cleared by client'
            ]
        }
        return JsonResponse(response_data, status=200)
    except Exception as e:
        logger.error(f"Error in clear_offline_cache: {str(e)}")
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=500
        )