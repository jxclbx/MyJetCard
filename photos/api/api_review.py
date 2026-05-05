import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..models import PendingPhoto
from ..services import approve_pending, reject_pending

PAGE_SIZE = 20


@login_required
@require_http_methods(["GET"])
def pending_list(request):
    status = request.GET.get("status", "pending").strip()
    page = int(request.GET.get("page", "1"))

    if request.user.is_staff or request.user.is_superuser:
        qs = PendingPhoto.objects.all()
    else:
        qs = PendingPhoto.objects.filter(user=request.user)

    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by("submitted_at")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    results = []
    for p in page_obj.object_list:
        results.append({
            "id": p.id,
            "status": p.status,
            "submitted_at": p.submitted_at.isoformat(),
            "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
            "review_note": p.review_note,

            "reg": p.reg,
            "model": p.model,
            "sub_model": p.sub_model,
            "airline": p.airline,
            "airport": p.airport,
            "date": p.date.isoformat(),
            "featured": p.featured,
            "is_special_livery": p.is_special_livery,
            "is_cargo": p.is_cargo,
            "is_bizjet": p.is_bizjet,
            "is_helicopter": p.is_helicopter,
            "is_rare": p.is_rare,

            "camera_name": p.camera.name if p.camera else "",
            "lens_name": p.lens.name if p.lens else "",

            "display_src": p.display_src,
            "display_src_sm": p.display_src_sm,
        })

    return JsonResponse({
        "results": results,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "count": paginator.count,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    })


@login_required
@require_http_methods(["POST"])
def pending_approve(request, pk: int):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Forbidden"}, status=403)

    p = get_object_or_404(PendingPhoto, pk=pk, status="pending")
    photo = approve_pending(p)
    return JsonResponse({"ok": True, "photo_id": photo.id})


@login_required
@require_http_methods(["POST"])
def pending_reject(request, pk: int):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"error": "Forbidden"}, status=403)

    p = get_object_or_404(PendingPhoto, pk=pk, status="pending")
    note = ""
    try:
        body = json.loads((request.body or b"{}").decode("utf-8"))
        note = (body.get("note") or "").strip()
    except Exception:
        note = ""
    reject_pending(p, note=note)
    return JsonResponse({"ok": True})
