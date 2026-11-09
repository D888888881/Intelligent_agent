from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="pinned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
