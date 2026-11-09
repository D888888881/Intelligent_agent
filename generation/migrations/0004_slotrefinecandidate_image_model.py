from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generation", "0003_slotrefinecandidate"),
    ]

    operations = [
        migrations.AddField(
            model_name="slotrefinecandidate",
            name="image_model",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
