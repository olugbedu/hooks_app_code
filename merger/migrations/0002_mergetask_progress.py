from django.db import migrations, models

class Migration(migrations.Migration):
  dependencies = [
    ('merger', '0001_initial'),
  ]

  operations = [
    migrations.AddField(
      model_name='mergetask',
      name='progress',
      field=models.IntegerField(default=0),
    ),
  ]
