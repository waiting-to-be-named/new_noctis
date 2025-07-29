# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0003_alter_notification_notification_type_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='ae_title',
            field=models.CharField(default='', max_length=16, help_text='DICOM Application Entity Title for PACS communication'),
            preserve_default=False,
        ),
    ]