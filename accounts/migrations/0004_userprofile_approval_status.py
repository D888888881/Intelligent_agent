from django.db import migrations, models


def approve_existing_users(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    User = apps.get_model("auth", "User")
    UserProfile.objects.filter(approval_status="approved").update(approval_status="approved")
    for profile in UserProfile.objects.all():
        user = User.objects.filter(pk=profile.user_id).first()
        if user and (user.is_superuser or user.is_staff or user.is_active):
            if profile.approval_status != "approved":
                profile.approval_status = "approved"
                profile.save(update_fields=["approval_status"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_userprofile_preferred_vision_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="approval_status",
            field=models.CharField(
                choices=[
                    ("pending", "待审批"),
                    ("approved", "已通过"),
                    ("rejected", "已拒绝"),
                ],
                default="approved",
                max_length=16,
            ),
        ),
        migrations.RunPython(approve_existing_users, migrations.RunPython.noop),
    ]
