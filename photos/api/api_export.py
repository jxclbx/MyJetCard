from __future__ import annotations

import csv
import io
import json
import zipfile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from ..models import DataExportLog, GearItem, PendingPhoto, Photo, SiteProfile

DAILY_EXPORT_LIMIT = 3


def _absolute_url(request, value):
    if not value:
        return ""
    return request.build_absolute_uri(value)


def _image_url(request, field):
    if not field:
        return ""
    try:
        return _absolute_url(request, field.url)
    except ValueError:
        return ""


def _source_pending_id(photo):
    try:
        return photo.source_pending.id
    except (PendingPhoto.DoesNotExist, AttributeError):
        return ""


def _gear_name(item):
    return item.name if item else ""


def _date_range_filter(qs, request):
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def _write_csv(rows, fieldnames):
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _photos_rows(request):
    qs = (
        _date_range_filter(Photo.objects.filter(user=request.user), request)
        .select_related("camera", "lens")
        .order_by("-date", "-id")
    )
    rows = []
    for p in qs.iterator():
        rows.append({
            "id": p.id,
            "username": request.user.username,
            "reg": p.reg,
            "model": p.model,
            "sub_model": p.sub_model,
            "airline": p.airline,
            "airport": p.airport,
            "date": p.date.isoformat() if p.date else "",
            "camera_name": _gear_name(p.camera),
            "lens_name": _gear_name(p.lens),
            "featured": p.featured,
            "is_special_livery": p.is_special_livery,
            "is_cargo": p.is_cargo,
            "is_bizjet": p.is_bizjet,
            "is_helicopter": p.is_helicopter,
            "is_rare": p.is_rare,
            "remarks": p.remarks,
            "src": p.src,
            "image_url": _image_url(request, p.image),
            "image_sm_url": _image_url(request, p.image_sm),
            "image_lg_url": _image_url(request, p.image_lg),
            "source_pending_id": _source_pending_id(p),
        })
    fields = [
        "id", "username", "reg", "model", "sub_model", "airline", "airport", "date",
        "camera_name", "lens_name", "featured", "is_special_livery", "is_cargo",
        "is_bizjet", "is_helicopter", "is_rare", "remarks", "src", "image_url",
        "image_sm_url", "image_lg_url", "source_pending_id",
    ]
    return fields, rows


def _pending_rows(request):
    qs = (
        _date_range_filter(PendingPhoto.objects.filter(user=request.user), request)
        .select_related("camera", "lens")
        .order_by("-submitted_at", "-id")
    )
    rows = []
    for p in qs.iterator():
        rows.append({
            "id": p.id,
            "username": request.user.username,
            "status": p.status,
            "reg": p.reg,
            "model": p.model,
            "sub_model": p.sub_model,
            "airline": p.airline,
            "airport": p.airport,
            "date": p.date.isoformat() if p.date else "",
            "camera_name": _gear_name(p.camera),
            "lens_name": _gear_name(p.lens),
            "featured": p.featured,
            "is_special_livery": p.is_special_livery,
            "is_cargo": p.is_cargo,
            "is_bizjet": p.is_bizjet,
            "is_helicopter": p.is_helicopter,
            "is_rare": p.is_rare,
            "remarks": p.remarks,
            "src": p.src,
            "image_url": _image_url(request, p.image),
            "image_sm_url": _image_url(request, p.image_sm),
            "review_note": p.review_note,
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else "",
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else "",
            "approved_photo_id": p.approved_photo_id or "",
        })
    fields = [
        "id", "username", "status", "reg", "model", "sub_model", "airline", "airport",
        "date", "camera_name", "lens_name", "featured", "is_special_livery", "is_cargo",
        "is_bizjet", "is_helicopter", "is_rare", "remarks", "src", "image_url",
        "image_sm_url", "review_note", "submitted_at", "reviewed_at", "approved_photo_id",
    ]
    return fields, rows


def _gear_rows(request):
    site = SiteProfile.objects.filter(user=request.user).first()
    qs = GearItem.objects.filter(site=site).order_by("kind", "name") if site else GearItem.objects.none()
    rows = [{"id": g.id, "kind": g.kind, "name": g.name} for g in qs.iterator()]
    return ["id", "kind", "name"], rows


def _site_profile_rows(request):
    site = SiteProfile.objects.filter(user=request.user).first()
    if not site:
        rows = []
    else:
        rows = [{
            "username": request.user.username,
            "location": site.location,
            "hobbies": site.hobbies,
            "avatar_url": _image_url(request, site.avatar),
            "banner_url": _image_url(request, site.banner),
            "pinned_ids": json.dumps(site.pinned_ids, ensure_ascii=False),
            "show_perf_panel": site.show_perf_panel,
            "gallery_page_size": site.gallery_page_size,
        }]
    return [
        "username", "location", "hobbies", "avatar_url", "banner_url", "pinned_ids",
        "show_perf_panel", "gallery_page_size",
    ], rows


TABLE_BUILDERS = {
    "photos": _photos_rows,
    "pending_photos": _pending_rows,
    "gear": _gear_rows,
    "site_profile": _site_profile_rows,
}


def _schema_payload():
    return {
        "version": 1,
        "format": "CSV files inside ZIP unless format=csv is requested for one table",
        "notes": [
            "Image files are not included; image columns contain URLs only.",
            "Dates use ISO formats.",
            "Boolean columns are exported as True/False.",
        ],
        "tables": {
            "photos": {
                "columns": [
                    "id", "username", "reg", "model", "sub_model", "airline", "airport", "date",
                    "camera_name", "lens_name", "featured", "is_special_livery", "is_cargo",
                    "is_bizjet", "is_helicopter", "is_rare", "remarks", "src", "image_url",
                    "image_sm_url", "image_lg_url", "source_pending_id",
                ],
            },
            "pending_photos": {
                "columns": [
                    "id", "username", "status", "reg", "model", "sub_model", "airline", "airport",
                    "date", "camera_name", "lens_name", "featured", "is_special_livery", "is_cargo",
                    "is_bizjet", "is_helicopter", "is_rare", "remarks", "src", "image_url",
                    "image_sm_url", "review_note", "submitted_at", "reviewed_at", "approved_photo_id",
                ],
            },
            "gear": {"columns": ["id", "kind", "name"]},
            "site_profile": {
                "columns": [
                    "username", "location", "hobbies", "avatar_url", "banner_url",
                    "pinned_ids", "show_perf_panel", "gallery_page_size",
                ],
            },
        },
    }


def _check_daily_limit(request):
    if request.user.is_staff or request.user.is_superuser:
        return None
    today = timezone.localdate()
    count = DataExportLog.objects.filter(user=request.user, created_at__date=today).count()
    if count >= DAILY_EXPORT_LIMIT:
        return JsonResponse({
            "error": "daily_limit_reached",
            "message": "You can export your data up to 3 times per day.",
        }, status=429)
    return None


@login_required
def export_my_data(request):
    limit_response = _check_daily_limit(request)
    if limit_response:
        return limit_response

    export_format = request.GET.get("format", "zip").lower()
    table = request.GET.get("table", "photos").lower()
    if export_format not in {"zip", "csv"}:
        return JsonResponse({"error": "invalid_format", "message": "Use format=zip or format=csv."}, status=400)
    if export_format == "csv" and table not in TABLE_BUILDERS:
        return JsonResponse({"error": "invalid_table", "message": "Unknown export table."}, status=400)

    log = DataExportLog.objects.create(user=request.user, format=export_format, table=table if export_format == "csv" else "")
    row_count = 0
    try:
        stamp = timezone.localtime(timezone.now()).strftime("%Y%m%d")
        if export_format == "csv":
            fields, rows = TABLE_BUILDERS[table](request)
            payload = _write_csv(rows, fields)
            row_count = len(rows)
            filename = f"myjetcard_{request.user.username}_{table}_{stamp}.csv"
            response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, builder in TABLE_BUILDERS.items():
                    fields, rows = builder(request)
                    row_count += len(rows)
                    archive.writestr(f"{name}.csv", _write_csv(rows, fields))
                archive.writestr("schema.json", json.dumps(_schema_payload(), ensure_ascii=False, indent=2))
                archive.writestr(
                    "README.txt",
                    "MyJetCard data export. Image files are not included; image columns contain URLs only.\n",
                )
            payload = zip_buffer.getvalue()
            filename = f"myjetcard_{request.user.username}_data_export_{stamp}.zip"
            response = HttpResponse(payload, content_type="application/zip")

        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "no-store"
        log.status = "completed"
        log.row_count = row_count
        log.file_size = len(payload)
        log.save(update_fields=["status", "row_count", "file_size"])
        return response
    except Exception:
        log.status = "failed"
        log.save(update_fields=["status"])
        raise
