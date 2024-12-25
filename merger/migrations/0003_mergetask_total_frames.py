from django.db import migrations, models

class Migration(migrations.Migration):
  dependencies = [
    ('merger', '0002_mergetask_progress'),
  ]

  operations = [
    migrations.AddField(
      model_name='mergetask',
      name='total_frames',
      field=models.IntegerField(default=0),
    ),
  ]
