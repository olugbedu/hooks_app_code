from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Define URL patterns for the application
urlpatterns = [
    # Include URLs from the account app
    path("", include("account.urls", namespace="account")),
    
    # Admin site URL
    path("admin/", admin.site.urls),
    
    # Include URLs from the hooks app
    path("hooks/", include("hooks.urls", namespace="hooks")),
    
    # Include URLs from the merger app
    path("merge/", include("merger.urls", namespace="merger")),
    
    # Password reset views
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/reset_password.html",
            email_template_name="password_reset_email_template.html",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
