import os
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import SiteProfile, GearItem
from ..forms import SiteProfileForm, GearItemForm



@login_required
def manage_site(request):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")
    """
    一个页面：
    - 编辑 SiteProfile（单例：只允许一个）
    - 显示 GearItem 列表
    - 新增 GearItem（在同页）
    """
    site = SiteProfile.objects.filter(user=request.user).first()
    if not site:
        site = SiteProfile.objects.create(user=request.user)

    old_avatar = site.avatar
    old_banner = site.banner

    if request.method == "POST":
        action = request.POST.get("action", "save_site")

        # A) 保存站点信息
        if action == "save_site":
            form = SiteProfileForm(request.POST, request.FILES, instance=site)
            gear_form = GearItemForm()  # 只是为了页面渲染
            if form.is_valid():
                updated = form.save()

                return redirect("photos_manage_site")

        # B) 新增 gear
        elif action == "add_gear":
            form = SiteProfileForm(instance=site)  # 只是为了页面渲染
            gear_form = GearItemForm(request.POST)
            if gear_form.is_valid():
                obj = gear_form.save(commit=False)
                obj.site = site
                obj.save()
                return redirect("photos_manage_site")

        else:
            form = SiteProfileForm(instance=site)
            gear_form = GearItemForm()

    else:
        form = SiteProfileForm(instance=site)
        gear_form = GearItemForm()

    gear_qs = GearItem.objects.filter(site=site).order_by("id")

    return render(request, "manage/user_profile_edit.html", {
        "site": site,
        "form": form,
        "gear_form": gear_form,
        "gear_items": gear_qs,
    })


@login_required
def manage_gear_edit(request, gear_id):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")
    gear = get_object_or_404(GearItem, id=gear_id, site__user=request.user)

    if request.method == "POST":
        form = GearItemForm(request.POST, instance=gear)
        if form.is_valid():
            form.save()
            return redirect("photos_manage_site")
    else:
        form = GearItemForm(instance=gear)

    return render(request, "manage/user_profile_gear_edit.html", {"gear": gear, "form": form})


@login_required
@require_POST
def manage_gear_delete(request, gear_id):
    if not request.user.is_superuser:
        return HttpResponse(f"<script>alert('网站目前为非交互，上传编辑功能暂不开放。');window.location.href='/{request.user.username}/';</script>")
    gear = get_object_or_404(GearItem, id=gear_id, site__user=request.user)
    gear.delete()
    return redirect("photos_manage_site")
