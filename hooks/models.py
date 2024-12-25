from django.db import models
from django.core.exceptions import ValidationError

def validate_video_file(value):
    """
    Validate the uploaded video file to ensure it is of an allowed MIME type.
    
    Args:
        value: The file to validate.
    
    Raises:
        ValidationError: If the file's MIME type is not in the list of valid types.
    """
    # Allowed video MIME types
    valid_mime_types = [
        'video/mp4', 'video/x-m4v', 'video/quicktime', 
        'video/x-msvideo', 'video/x-ms-wmv'
    ]
    file_mime_type = value.file.content_type

    # Raise an error if the file type is not valid
    if file_mime_type not in valid_mime_types:
        raise ValidationError(
            f'Unsupported file type: {file_mime_type}. Please upload a valid video file.'
        )

class Hook(models.Model):
    """
    Model representing a Hook with various attributes including video content, 
    Google Sheets link, API key, and visual properties.
    """
    hooks_content = models.FileField(
        max_length=500,
        upload_to='hooks_videos/',
        blank=True,
        null=True,
        validators=[validate_video_file]
    )
    google_sheets_link = models.URLField(max_length=500, blank=True, null=True)
    eleven_labs_api_key = models.CharField(max_length=255, blank=True, null=True)
    voice_id = models.CharField(max_length=255, blank=True, null=True)
    box_color = models.CharField(max_length=7, default='#485AFF')
    font_color = models.CharField(max_length=7, default='#FFFFFF')
    task_id = models.CharField(max_length=1000, unique=True)
    parallel_processing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Choices for the dimension field
    STATUS_CHOICES = [
        ('option1', 'option1'), 
        ('option2', 'option2'), 
        ('option3', 'option3'),
        ('option4', 'option4')
    ]
    dimension = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='option1'
    )

    def __str__(self):
        """Return a string representation of the Hook object."""
        return str(self.id)

class Task(models.Model):
    """
    Model representing a Task with attributes such as task ID, status, 
    aspect ratio, and associated video links.
    """
    task_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='processing')
    aspect_ratio = models.CharField(max_length=255, default='option1')
    video_links = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        """Return a string representation of the Task object."""
        return self.status

class Package(models.Model):
    """
    Model representing a Package with attributes such as name, price, 
    Stripe ID, video limit, and price per video.
    """
    name = models.CharField(max_length=100)
    price = models.PositiveIntegerField()
    stripe_id = models.CharField(max_length=200)
    video_limit = models.PositiveIntegerField()
    price_per_video = models.FloatField(null=True, blank=True)

    def __str__(self) -> str:
        """Return a string representation of the Package object."""
        return self.name
