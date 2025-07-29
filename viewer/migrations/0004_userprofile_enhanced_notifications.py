# Generated manually for UserProfile and enhanced notifications

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0003_alter_notification_notification_type_chatmessage'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_type', models.CharField(choices=[('radiologist', 'Radiologist'), ('technologist', 'Technologist'), ('admin', 'Administrator'), ('facility_staff', 'Facility Staff'), ('resident', 'Resident'), ('fellow', 'Fellow')], default='radiologist', max_length=20)),
                ('medical_license', models.CharField(blank=True, max_length=50)),
                ('specialization', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('is_active_staff', models.BooleanField(default=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pictures/')),
                ('bio', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='staff', to='viewer.facility')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='auth.user')),
            ],
            options={
                'ordering': ['user__username'],
            },
        ),
        migrations.AddField(
            model_name='notification',
            name='sender',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sent_notifications', to='auth.user'),
        ),
        migrations.AddField(
            model_name='notification',
            name='related_facility',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.facility'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(choices=[('new_study', 'New Study Upload'), ('report_ready', 'Report Ready'), ('ai_complete', 'AI Analysis Complete'), ('system_error', 'System Error'), ('system', 'System Message'), ('chat', 'Chat Message'), ('user_mention', 'User Mention'), ('facility_update', 'Facility Update'), ('report_assigned', 'Report Assigned')], max_length=20),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='message_type',
            field=models.CharField(choices=[('system_upload', 'System Upload'), ('user_chat', 'User Chat'), ('facility_broadcast', 'Facility Broadcast'), ('study_discussion', 'Study Discussion')], default='user_chat', max_length=20),
        ),
    ]