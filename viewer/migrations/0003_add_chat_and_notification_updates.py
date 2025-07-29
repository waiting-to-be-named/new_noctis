# Generated manually for Chat model and notification updates

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('viewer', '0002_add_dicom_image_fields'),
    ]

    operations = [
        # Update Notification model with new choices
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('new_study', 'New Study Upload'), ('report_ready', 'Report Ready'), ('ai_complete', 'AI Analysis Complete'), ('system', 'System Message'), ('system_error', 'System Error'), ('new_chat', 'New Chat Message')], max_length=20),
        ),
        # Create Chat model
        migrations.CreateModel(
            name='Chat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(choices=[('user_message', 'User Message'), ('system_upload', 'System Upload Notification'), ('system_error', 'System Error')], default='user_message', max_length=20)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='viewer.facility')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
                ('study', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='viewer.dicomstudy')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]