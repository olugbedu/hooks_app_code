from django.urls import path
from . import views

# Define the app name for namespacing URL names
app_name = 'merger'

# URL patterns for the merger app
urlpatterns = [
    # Home page
    path('', views.index, name='index'),
    
    # Upload files page
    path('upload/', views.upload_files, name='upload_files'),
    
    # Processing page for a specific task
    path('processing/<str:task_id>/', views.processing, name='processing'),
    
    # Get progress of a specific task
    path('get_progress/<str:task_id>/', views.get_progress, name='get_progress'),
    
    # Check status of a specific task
    path('check_status/<str:task_id>/', views.check_task_status, name='check_status'),
    
    # Download zip file for a specific task
    path('download_zip/<str:task_id>/', views.download_zip, name='download_zip'),
    
    # Download output video by path
    path('download_output/', views.download_video, name='download_output'),
    
    # Processing successful page for a specific task
    path('processing_successful/<str:task_id>/', views.processing_successful, name='processing_successful'),
]
