from django.urls import path
from . import views

# Define the application namespace
app_name = 'hooks'

# URL patterns for the hooks app
urlpatterns = [
    # URL pattern for uploading a hook
    path('upload/', views.upload_hook, name='upload'),

    # URL pattern for processing a task with a specific task_id and aspect_ratio
    path('processing/<str:task_id>/<str:aspect_ratio>/', views.processing, name='processing'),

    # URL pattern to check the status of a task using task_id
    path('check_status/<str:task_id>/', views.check_task_status, name='check_status'),

    # URL pattern to download a zip file associated with a task_id
    path('download_zip/<str:task_id>/', views.download_zip, name='download_zip'),

    # URL pattern to download a video output using the video path
    path('download-video/', views.download_video, name='download_video'), 

    # URL pattern for indicating successful processing of a task using task_id
    path('processing_successful/<str:task_id>/', views.processing_successful, name='processing_successful'),

    # URL pattern to validate a Google Sheets link
    path('validate-google-sheet-link/', views.validate_google_sheet_link, name='validate_google_sheet_link'),

    # URL pattern to validate an API key
    path('validate-api-key/', views.validate_api_key, name='validate_api_key'),
]
