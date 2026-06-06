from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Photo, PendingPhoto, SiteProfile
from ..services import get_model_choices, get_model_submodel_map
from ..forms import PendingPhotoCreateForm, PendingPhotoEditForm


@login_required
def manage_pending_list(request):
    qs = PendingPhoto.objects.filter(user=request.user).order_by("-submitted_at", "-id")

    page = int(request.GET.get("page", "1"))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page)

    return render(request, "manage/my_pending_list.html", {
        "photos": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
def manage_pending_edit(request, pending_id):
    pending = get_object_or_404(PendingPhoto, id=pending_id)

    if pending.user != request.user and not request.user.is_staff:
        raise Http404("You do not have permission to edit this pending photo.")

    site = SiteProfile.objects.filter(user=pending.user).first()
    is_draft = pending.status == "draft"

    if request.method == "POST":
        if is_draft:
            form = PendingPhotoCreateForm(request.POST, request.FILES, instance=pending, site=site)
        else:
            form = PendingPhotoEditForm(request.POST, instance=pending, site=site)
        if form.is_valid():
            p = form.save(commit=False)
            if is_draft and request.FILES.get("image"):
                p.status = "pending"
            p.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok'})
            if request.user.is_staff:
                return redirect("review_queue")
            return redirect("photos_manage_pending_list")
    else:
        if is_draft:
            form = PendingPhotoCreateForm(instance=pending, site=site)
        else:
            form = PendingPhotoEditForm(instance=pending, site=site)

    airlines = Photo.objects.values_list('airline', flat=True).distinct().order_by('airline')

    return render(request, "manage/my_pending_photo_detail_edit.html", {
        "photo": pending,
        "form": form,
        "is_draft": is_draft,
        "airlines": airlines,
        "models": get_model_choices(),
        "model_submodel_map": get_model_submodel_map(),
    })


@login_required
def submit_pending_page(request):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")
    site = SiteProfile.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = PendingPhotoCreateForm(request.POST, request.FILES, site=site)
        if form.is_valid():
            pending = form.save(commit=False)
            pending.user = request.user
            pending.status = "pending" if pending.image else "draft"
            pending.save()
            if pending.status == "pending":
                messages.success(request, f"Photo {pending.reg} submitted successfully! You can submit another one.")
            else:
                messages.success(request, f"Draft saved: {pending.reg}. Upload a photo later to submit for review.")
            return redirect("submit_pending")
    else:
        form = PendingPhotoCreateForm(site=site)
    airlines = Photo.objects.values_list('airline', flat=True).distinct().order_by('airline')
    return render(request, "manage/photo_submit.html", {
        "form": form,
        "airlines": airlines,
        "models": get_model_choices(),
        "model_submodel_map": get_model_submodel_map(),
    })


@login_required
def review_queue_page(request):
    if not request.user.is_staff:
        return HttpResponse(f"<script>alert('只有网站管理员可以访问此页面。'); window.location.href = '/{request.user.username}/';</script>")
    return render(request, "staff/site_review_queue.html")
