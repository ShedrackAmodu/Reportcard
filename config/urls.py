from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from apps.accounts.views import dashboard
from apps.pages import pwa_views

admin.site.site_header = 'Django Administration'
admin.site.site_title = 'Django Site Admin'
admin.site.index_title = 'Django Administration'

DJANGO_ADMIN_URL = settings.DJANGO_ADMIN_URL + '/'
urlpatterns = [
    # admin_honeypot doesn't support Django 4
    # path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path(DJANGO_ADMIN_URL, admin.site.urls),
    path('', include('apps.pages.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('dashboard/', dashboard, name='index_view'),
    path('accounts/', include('allauth.urls')),
    path('blog/', include('apps.articles.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('account/', include('apps.accounts.urls')),
    path('academics/', include('apps.academics.urls')),
    path('notices/', include('apps.notices.site_urls')),
    path('notices/dashboard/', include('apps.notices.dashboard_urls')),
    path('students/', include('apps.students.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('teachers/', include('apps.teachers.urls')),
    path('result/', include('apps.result.urls')),
    path('institute/', include('apps.institute.urls')),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='account/password/password_reset.html'
        ),
        name="password_reset",
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='account/password/password_reset_done.html'
        ),
        name="password_reset_done",
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='account/password/password_reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='account/password/password-reset-complete.html'
        ),
        name='password_reset_complete'
    ),
    path('dashboard/payments/', include('apps.payments.urls')),
    # API URLS
    path('api/', include('apps.articles.api.routes')),
    path('upload/', include('django_file_form.urls')),
    path('service-worker.js', pwa_views.service_worker, name='service_worker'),
    path('offline/', pwa_views.offline, name='offline'),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT
)

if "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
