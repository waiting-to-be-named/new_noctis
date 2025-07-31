# Generated manually for adding AE title to Facility model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0003_alter_notification_notification_type_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='ae_title',
            field=models.CharField(
                max_length=16,
                unique=True,
                help_text='DICOM AE Title for this facility',
                null=True,  # Allow null for existing records
                blank=True
            ),
        ),
    ]