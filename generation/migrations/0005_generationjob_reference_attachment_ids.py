from django.db import migrations, models


def copy_fk_to_ids(apps, schema_editor):
    GenerationJob = apps.get_model("generation", "GenerationJob")
    for job in GenerationJob.objects.exclude(reference_attachment_id=None):
        if not job.reference_attachment_ids:
            job.reference_attachment_ids = [job.reference_attachment_id]
            job.save(update_fields=["reference_attachment_ids"])


class Migration(migrations.Migration):
    dependencies = [
        ("generation", "0004_slotrefinecandidate_image_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationjob",
            name="reference_attachment_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(copy_fk_to_ids, migrations.RunPython.noop),
    ]
