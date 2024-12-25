from django.contrib import admin
from .models import MergeTask

# Register the MergeTask model with the admin site
@admin.register(MergeTask)
class TaskAdmin(admin.ModelAdmin):
    # Define the fields to be displayed in the admin list view
    list_display = ['task_id', 'status', 'short_video_path', 'large_video_paths', 'video_links']