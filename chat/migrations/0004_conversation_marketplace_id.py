from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_conversation_share_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="marketplace_id",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
