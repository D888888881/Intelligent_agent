from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_userprofile_approval_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="real_name",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
