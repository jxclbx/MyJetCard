from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Count


def clean_pending_photo_links(apps, schema_editor):
    Photo = apps.get_model("photos", "Photo")
    PendingPhoto = apps.get_model("photos", "PendingPhoto")

    valid_photo_ids = set(Photo.objects.values_list("id", flat=True))
    valid_pending_ids = set(PendingPhoto.objects.values_list("id", flat=True))

    PendingPhoto.objects.exclude(approved_photo_id__isnull=True).exclude(
        approved_photo_id__in=valid_photo_ids
    ).update(approved_photo_id=None)

    Photo.objects.exclude(pending_photo_id__isnull=True).exclude(
        pending_photo_id__in=valid_pending_ids
    ).update(pending_photo_id=None)

    # Backfill from the old Photo -> PendingPhoto link when the pending row
    # does not already have an approved photo recorded.
    for photo_id, pending_id in Photo.objects.exclude(
        pending_photo_id__isnull=True
    ).values_list("id", "pending_photo_id").iterator():
        PendingPhoto.objects.filter(
            id=pending_id,
            approved_photo_id__isnull=True,
        ).update(approved_photo_id=photo_id)

    # The new OneToOneField requires each Photo to be claimed by at most one
    # pending row. Keep the direct old reverse link when it exists; otherwise
    # keep the most recently reviewed/submitted row and clear the rest.
    duplicates = (
        PendingPhoto.objects.exclude(approved_photo_id__isnull=True)
        .values("approved_photo_id")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )

    for duplicate in duplicates:
        photo_id = duplicate["approved_photo_id"]
        candidate_ids = list(
            PendingPhoto.objects.filter(approved_photo_id=photo_id).values_list(
                "id", flat=True
            )
        )
        preferred_id = (
            Photo.objects.filter(id=photo_id).values_list(
                "pending_photo_id", flat=True
            ).first()
        )
        if preferred_id not in candidate_ids:
            preferred_id = (
                PendingPhoto.objects.filter(id__in=candidate_ids, status="approved")
                .order_by("-reviewed_at", "-submitted_at", "-id")
                .values_list("id", flat=True)
                .first()
            )
        if preferred_id is None:
            preferred_id = (
                PendingPhoto.objects.filter(id__in=candidate_ids)
                .order_by("-reviewed_at", "-submitted_at", "-id")
                .values_list("id", flat=True)
                .first()
            )

        PendingPhoto.objects.filter(id__in=candidate_ids).exclude(
            id=preferred_id
        ).update(approved_photo_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("photos", "0015_add_pending_photo_id_to_photo"),
    ]

    operations = [
        migrations.RunPython(clean_pending_photo_links, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="pendingphoto",
            old_name="approved_photo_id",
            new_name="approved_photo",
        ),
        migrations.AlterField(
            model_name="pendingphoto",
            name="approved_photo",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_pending",
                to="photos.photo",
            ),
        ),
        migrations.RemoveField(
            model_name="photo",
            name="pending_photo_id",
        ),
    ]
