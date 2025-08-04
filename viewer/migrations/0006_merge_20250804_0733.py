# Generated manually to merge conflicting migrations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0004_remove_test_data_field'),
        ('viewer', '0005_add_dicom_port'),
    ]

    operations = [
    ]