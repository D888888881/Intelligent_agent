import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import generation.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("generation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SlotRefineCandidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot_index", models.PositiveSmallIntegerField()),
                ("prompt", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("applied", "Applied"),
                            ("discarded", "Discarded"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("file", models.ImageField(blank=True, upload_to=generation.models.slot_refine_candidate_path)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refine_candidates",
                        to="generation.generationjob",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slot_refine_candidates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
