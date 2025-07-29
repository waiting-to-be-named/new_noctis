# Generated manually for FacilityUser model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacilityUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=150, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='viewer.facility')),
            ],
            options={
                'verbose_name_plural': 'Facility Users',
                'ordering': ['username'],
            },
        ),
        migrations.AddField(
            model_name='dicomstudy',
            name='facility_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.facilityuser'),
        ),
        migrations.AlterField(
            model_name='dicomstudy',
            name='facility',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='viewer.facility'),
        ),
    ]