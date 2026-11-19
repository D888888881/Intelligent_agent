from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("uploads", "0001_initial"),
        ("generation", "0005_generationjob_reference_attachment_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="slotrefinecandidate",
            name="reference_mode",
            field=models.CharField(
                choices=[("dual", "商品原图+当前成图"), ("upload_only", "仅新上传参考")],
                default="dual",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="slotrefinecandidate",
            name="reference_attachment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="slot_refine_candidates",
                to="uploads.attachment",
            ),
        ),
    ]