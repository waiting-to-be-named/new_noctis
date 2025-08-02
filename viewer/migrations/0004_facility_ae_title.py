from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viewer', '0003_add_test_data_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='facility',
            name='ae_title',
            field=models.CharField(max_length=16, unique=True, null=True, blank=True),
        ),
    ]