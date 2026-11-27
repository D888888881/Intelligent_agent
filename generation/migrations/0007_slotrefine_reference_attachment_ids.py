from django.db import migrations, models


def copy_single_upload_ref(apps, schema_editor):
    SlotRefineCandidate = apps.get_model("generation", "SlotRefineCandidate")
    for row in SlotRefineCandidate.objects.exclude(reference_attachment_id=None):
        if not row.reference_attachment_ids:
            row.reference_attachment_ids = [row.reference_attachment_id]
            row.save(update_fields=["reference_attachment_ids"])


class Migration(migrations.Migration):
    dependencies = [
        ("generation", "0006_slotrefine_reference_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="slotrefinecandidate",
            name="reference_attachment_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(copy_single_upload_ref, migrations.RunPython.noop),
    ]
