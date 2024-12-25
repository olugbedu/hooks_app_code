import hooks.models
from django.db import migrations, models

class Migration(migrations.Migration):
  dependencies = [
    ('hooks', '0002_hook_dimension_task_aspect_ratio'),
  ]

  operations = [
    migrations.AlterField(
      model_name='hook',
      name='hooks_content',
      field=models.FileField(
        blank=True,
        max_length=10485760,
        null=True,
        upload_to='hooks_videos/',
        validators=[hooks.models.validate_video_file]
      ),
    ),
  ]
