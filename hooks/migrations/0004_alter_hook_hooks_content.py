import hooks.models
from django.db import migrations, models

class Migration(migrations.Migration):
  dependencies = [
    ('hooks', '0003_alter_hook_hooks_content'),
  ]

  operations = [
    migrations.AlterField(
      model_name='hook',
      name='hooks_content',
      field=models.FileField(
        blank=True,
        max_length=500,
        null=True,
        upload_to='hooks_videos/',
        validators=[hooks.models.validate_video_file]
      ),
    ),
  ]
