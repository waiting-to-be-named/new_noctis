# Generated manually to add test_data field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0002_add_dicom_image_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='dicomimage',
            name='test_data',
            field=models.BooleanField(default=False),
        ),
    ]