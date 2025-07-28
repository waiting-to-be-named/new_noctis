# Generated manually for enhanced DICOM viewer features

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('address', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('letterhead_logo', models.ImageField(blank=True, null=True, upload_to='letterheads/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Facilities',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='WorklistPatient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('patient_name', models.CharField(max_length=200)),
                ('patient_id', models.CharField(max_length=100)),
                ('birth_date', models.DateField(blank=True, null=True)),
                ('sex', models.CharField(blank=True, max_length=10)),
                ('study_date', models.DateField(blank=True, null=True)),
                ('study_time', models.TimeField(blank=True, null=True)),
                ('modality', models.CharField(max_length=10)),
                ('scheduled_station_ae_title', models.CharField(blank=True, max_length=50)),
                ('study_description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_viewed', models.BooleanField(default=False)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='worklist_patients', to='viewer.facility')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='dicomstudy',
            name='facility',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='studies', to='viewer.facility'),
        ),
        migrations.AddField(
            model_name='dicomstudy',
            name='worklist_patient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='viewer.worklistpatient'),
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('findings', models.TextField()),
                ('impression', models.TextField()),
                ('recommendations', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('final', 'Final'), ('amended', 'Amended')], default='draft', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_reports', to=settings.AUTH_USER_MODEL)),
                ('signed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signed_reports', to=settings.AUTH_USER_MODEL)),
                ('study', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='report', to='viewer.dicomstudy')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('new_study', 'New Study'), ('report_ready', 'Report Ready'), ('urgent', 'Urgent')], default='new_study', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.facility')),
                ('study', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.dicomstudy')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ClinicalInformation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chief_complaint', models.TextField(blank=True)),
                ('clinical_history', models.TextField(blank=True)),
                ('indication', models.TextField(blank=True)),
                ('allergies', models.TextField(blank=True)),
                ('medications', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('study', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='clinical_info', to='viewer.dicomstudy')),
            ],
        ),
        migrations.AlterField(
            model_name='measurement',
            name='measurement_type',
            field=models.CharField(choices=[('line', 'Line Measurement'), ('angle', 'Angle Measurement'), ('area', 'Area Measurement'), ('ellipse', 'Ellipse ROI')], default='line', max_length=10),
        ),
        migrations.AlterField(
            model_name='measurement',
            name='unit',
            field=models.CharField(choices=[('px', 'Pixels'), ('mm', 'Millimeters'), ('cm', 'Centimeters'), ('HU', 'Hounsfield Units')], default='px', max_length=10),
        ),
        migrations.AddField(
            model_name='measurement',
            name='mean_hu',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='std_hu',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='min_hu',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='max_hu',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='annotation',
            name='font_size',
            field=models.IntegerField(default=14),
        ),
        migrations.AddField(
            model_name='annotation',
            name='color',
            field=models.CharField(default='#FFFF00', max_length=7),
        ),
        migrations.AddField(
            model_name='annotation',
            name='is_draggable',
            field=models.BooleanField(default=True),
        ),
    ]