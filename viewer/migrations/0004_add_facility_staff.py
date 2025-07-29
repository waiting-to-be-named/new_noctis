# Generated migration for adding staff relationship to Facility

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('viewer', '0003_alter_notification_notification_type_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='staff',
            field=models.ManyToManyField(blank=True, related_name='facilities', to=settings.AUTH_USER_MODEL),
        ),
    ]