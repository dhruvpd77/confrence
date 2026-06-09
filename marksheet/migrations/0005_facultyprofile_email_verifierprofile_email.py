from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marksheet', '0004_alter_paperevaluation_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='facultyprofile',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='verifierprofile',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
