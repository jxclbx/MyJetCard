from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Photo, SiteProfile
from ..services import get_model_choices, get_model_submodel_map
from ..forms import PhotoCreateForm, PhotoEditForm


@login_required
def manage_photo_list(request):
    qs = Photo.objects.filter(user=request.user).order_by("-date", "-id")

    q = request.GET.get("q", "").strip()
    if q:
        q_clean = q.replace("-", "")
        qs = qs.annotate(
            clean_reg_q=Replace('reg', Value('-'), Value(''))
        ).filter(
            Q(clean_reg_q__icontains=q_clean) |
            Q(model__icontains=q) |
            Q(sub_model__icontains=q) |
            Q(airline__icontains=q) |
            Q(airport__icontains=q)
        )

    page = int(request.GET.get("page", "1"))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page)

    return render(request, "manage/my_photo_list.html", {
        "photos": page_obj.object_list,
        "page_obj": page_obj,
        "query": q,
    })


@login_required
def manage_photo_add(request):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")
    site = SiteProfile.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = PhotoCreateForm(request.POST, request.FILES, site=site)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.user = request.user
            photo.save()
            messages.success(request, f"Photo {photo.reg} added directly to database! You can add another one.")
            return redirect("photos_manage_add")
    else:
        form = PhotoCreateForm(site=site)
    airlines = Photo.objects.values_list('airline', flat=True).distinct().order_by('airline')
    return render(request, "staff/staff_photo_submit.html", {
        "form": form,
        "airlines": airlines,
        "models": get_model_choices(),
        "model_submodel_map": get_model_submodel_map(),
    })


@login_required
def manage_photo_edit(request, photo_id):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")

    # owner 或 staff 均可编辑
    if request.user.is_staff:
        photo = get_object_or_404(Photo, id=photo_id)
    else:
        photo = get_object_or_404(Photo, id=photo_id, user=request.user)

    site = SiteProfile.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = PhotoEditForm(request.POST, instance=photo, site=site)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok'})
            return redirect("photos_manage_list")
    else:
        form = PhotoEditForm(instance=photo, site=site)

    airlines = Photo.objects.values_list('airline', flat=True).distinct().order_by('airline')
    return render(request, "manage/my_photo_detail_edit.html", {
        "photo": photo,
        "form": form,
        "airlines": airlines,
        "models": get_model_choices(),
        "model_submodel_map": get_model_submodel_map(),
    })


@login_required
@require_POST
def manage_photo_delete(request, photo_id):
    # owner 或 staff 均可删除
    if request.user.is_staff:
        p = get_object_or_404(Photo, id=photo_id)
    else:
        p = get_object_or_404(Photo, id=photo_id, user=request.user)
    p.delete()

    nxt = request.GET.get("next")
    return redirect(nxt or "photos_manage_list")


@login_required
def manage_photo_replace_image(request, photo_id):
    """
    仅 staff/admin 可用：上传新图替换掉现有照片的 image / image_sm / image_lg。
    不删除旧文件（由全局清理命令统一处理），不影响 pending 记录。
    """
    if not request.user.is_staff:
        raise Http404

    photo = get_object_or_404(Photo, id=photo_id)

    if request.method == "POST":
        new_image = request.FILES.get("image")
        if new_image:
            # 直接赋值给 image 字段，Photo.save() 会自动重新生成 sm/lg
            photo.image = new_image
            photo.save()

            nxt = request.GET.get("next")
            return redirect(nxt or "photos_manage_list")

    return render(request, "staff/photo_replace.html", {
        "photo": photo,
    })
