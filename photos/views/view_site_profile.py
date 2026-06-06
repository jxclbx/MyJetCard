from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import GearItemForm, SiteProfileForm
from ..models import GearItem, SiteProfile

PAGE_SIZE_MIN = 4
PAGE_SIZE_MAX = 100
PAGE_SIZE_DEFAULT = 24


def clean_page_size(value):
    try:
        size = int(value)
    except (TypeError, ValueError):
        return PAGE_SIZE_DEFAULT
    size = max(PAGE_SIZE_MIN, min(PAGE_SIZE_MAX, size))
    return size - (size % 4)


def upload_edit_disabled_response(request):
    return HttpResponse(
        "<script>alert('网站目前为非交互，上传编辑功能暂不开放。');"
        f"window.location.href='/{request.user.username}/';</script>"
    )


@login_required
def manage_site(request):
    site = SiteProfile.objects.filter(user=request.user).first()
    if not site:
        site = SiteProfile.objects.create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action", "save_site")

        if action == "save_page_sizes":
            site.gallery_page_size = clean_page_size(request.POST.get("gallery_page_size"))
            site.save(update_fields=["gallery_page_size"])
            return redirect("photos_manage_site")

        if not request.user.is_superuser:
            return upload_edit_disabled_response(request)

        if action == "save_site":
            form = SiteProfileForm(request.POST, request.FILES, instance=site)
            gear_form = GearItemForm()
            if form.is_valid():
                form.save()
                return redirect("photos_manage_site")
        elif action == "add_gear":
            form = SiteProfileForm(instance=site)
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
        return upload_edit_disabled_response(request)
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
        return upload_edit_disabled_response(request)
    gear = get_object_or_404(GearItem, id=gear_id, site__user=request.user)
    gear.delete()
    return redirect("photos_manage_site")
