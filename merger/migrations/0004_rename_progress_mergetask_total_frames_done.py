from django.db import migrations

class Migration(migrations.Migration):
  dependencies = [
    ('merger', '0003_mergetask_total_frames'),
  ]

  operations = [
    migrations.RenameField(
      model_name='mergetask',
      old_name='progress',
      new_name='total_frames_done',
    ),
  ]
