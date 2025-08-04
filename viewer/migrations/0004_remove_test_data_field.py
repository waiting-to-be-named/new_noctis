# Generated manually to remove test_data field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0003_add_test_data_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dicomimage',
            name='test_data',
        ),
    ]