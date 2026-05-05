from django.http import JsonResponse
from ..models import SiteProfile, GearItem
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

def api_site(request, username):
    user = get_object_or_404(User, username=username)
    site, _ = SiteProfile.objects.get_or_create(user=user)

    # 只取需要的字段：id / kind / name
    gear_items = GearItem.objects.filter(site=site).values("id", "kind", "name")

    cameras = []
    lenses = []
    for item in gear_items:
        if item["kind"] == "camera":
            cameras.append({"id": item["id"], "name": item["name"]})
        elif item["kind"] == "lens":
            lenses.append({"id": item["id"], "name": item["name"]})

    return JsonResponse({
        "site": {
            "location": site.location,
            "hobbies": site.hobbies,
            "avatar": site.avatar.url if site.avatar else "",
            "banner": site.banner.url if site.banner else "",
            "gear": {
                "cameras": cameras,
                "lenses": lenses
            },
        }
    })
