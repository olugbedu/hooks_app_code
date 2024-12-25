from django.db import models

# Model to represent a merge task
class MergeTask(models.Model):
    # Unique identifier for the task
    task_id = models.CharField(max_length=255)
    
    # Status of the task, default is 'processing'
    status = models.CharField(max_length=20, default='processing')
    
    # Path to the short video, stored as JSON
    short_video_path = models.JSONField(null=True, blank=True)
    
    # Paths to the large videos, stored as JSON
    large_video_paths = models.JSONField(null=True, blank=True)
    
    # Links to the videos, stored as JSON
    video_links = models.JSONField(null=True, blank=True)
    
    # Number of frames processed so far
    total_frames_done = models.IntegerField(default=0)
    
    # Total number of frames in the video
    total_frames = models.IntegerField(default=0)

    # String representation of the model
    def __str__(self) -> str:
        return self.status
