# Generated manually for the experimental data export feature.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("photos", "0017_alter_pendingphoto_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DataExportLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("format", models.CharField(default="zip", max_length=16)),
                ("table", models.CharField(blank=True, default="", max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[("started", "Started"), ("completed", "Completed"), ("failed", "Failed")],
                        default="started",
                        max_length=16,
                    ),
                ),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("file_size", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_export_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["user", "-created_at"], name="idx_export_user_time")],
            },
        ),
    ]
