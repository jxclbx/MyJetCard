from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist

from .models import AircraftSubModel, Photo, SiteProfile, GearItem


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("user","id", "reg", "model", "airline", "airport", "date", "featured", "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare", "source_pending_id")
    list_filter = ("user","featured", "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare", "airport", "airline", "model", "date")
    search_fields = ("reg", "model", "sub_model", "airline", "airport", "remarks")
    ordering = ("-date", "-id")
    list_per_page = 50

    def source_pending_id(self, obj):
        try:
            return obj.source_pending.id
        except ObjectDoesNotExist:
            return None
    source_pending_id.short_description = "source pending"


class GearItemInline(admin.TabularInline):
    model = GearItem
    extra = 0
    fields = ("kind", "name")       
    ordering = ("kind", "name")     
    show_change_link = True


@admin.register(SiteProfile)
class SiteProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "location", "hobbies")
    search_fields = ("location", "hobbies")
    inlines = [GearItemInline]

    fieldsets = (
        ("baseinfo", {"fields": ("location", "hobbies")}),
        ("images", {"fields": ("avatar", "banner")}),
        ("Editor's Picks (JSON input example '[1, 2, 3]')", {"fields": ("pinned_ids",)}),
    )

    def has_add_permission(self, request):
        return not SiteProfile.objects.exists()


@admin.register(GearItem)
class GearItemAdmin(admin.ModelAdmin):
    """
    Gear 单独管理页
    """
    list_display = ("id", "site", "kind", "name")
    list_filter = ("site", "kind")
    search_fields = ("name",)                   
    ordering = ("site", "kind", "name")         


@admin.register(AircraftSubModel)
class AircraftSubModelAdmin(admin.ModelAdmin):
    list_display = ("model", "sub_model", "usage_count", "updated_at")
    search_fields = ("model", "sub_model")
    ordering = ("model", "sub_model")
    readonly_fields = ("usage_count", "updated_at")

from .models import PendingPhoto

@admin.register(PendingPhoto)
class PendingPhotoAdmin(admin.ModelAdmin):
    list_display = ("user","id","status","reg","model","airline","airport","date","featured","is_special_livery","is_cargo","is_bizjet","is_helicopter","is_rare","approved_photo")
    list_filter = ("user","status","featured","is_special_livery","is_cargo","is_bizjet","is_helicopter","is_rare","airport","airline","model")
    search_fields = ("reg","model","airline","airport","remarks","sub_model")
    ordering = ("-submitted_at",)
