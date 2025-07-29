# Generated manually to fix worklist facility issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0002_add_dicom_image_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='worklistentry',
            name='facility',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='viewer.facility'),
        ),
    ]