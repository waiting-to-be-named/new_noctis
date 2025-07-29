# Generated manually for ChatMessage model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_type', models.CharField(choices=[('system', 'System Message'), ('chat', 'Chat Message'), ('upload', 'Upload Notification'), ('error', 'Error Message')], default='chat', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to='auth.user')),
                ('related_study', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.dicomstudy')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('new_study', 'New Study Upload'), ('report_ready', 'Report Ready'), ('ai_complete', 'AI Analysis Complete'), ('system', 'System Message'), ('chat', 'Chat Message'), ('upload_error', 'Upload Error')], max_length=20),
        ),
    ]