from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_userprofile_real_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_marketplace_id",
            field=models.CharField(blank=True, default="tk_shop_mx", max_length=32),
        ),
    ]
