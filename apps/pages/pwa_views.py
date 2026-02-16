from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


def service_worker(request):
    """Serve service worker from root scope for full-site offline support."""
    sw_path = Path(settings.BASE_DIR) / 'static' / 'pwa' / 'service-worker.js'
    content = sw_path.read_text(encoding='utf-8')
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def offline(request):
    return render(request, 'pages/offline.html')

