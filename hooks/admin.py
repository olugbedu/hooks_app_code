from django.contrib import admin
from .models import Hook, Task

# Register the Hook model with the admin site
@admin.register(Hook)
class HookAdmin(admin.ModelAdmin):
    # Define the fields to display in the admin list view for Hook
    list_display = ['hooks_content', 'google_sheets_link', 'eleven_labs_api_key', 'voice_id']

# Register the Task model with the admin site
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # Define the fields to display in the admin list view for Task
    list_display = ['task_id', 'status', 'video_links']