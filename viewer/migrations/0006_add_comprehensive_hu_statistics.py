# Generated migration for comprehensive HU statistics

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0005_add_dicom_port'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_median',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_percentile_25',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_percentile_75',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_cv',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_ci_lower',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_ci_upper',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='hounsfield_pixel_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]