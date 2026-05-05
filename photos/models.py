from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

import io
import os
from PIL import Image, ImageEnhance
from django.core.files.base import ContentFile

THUMB_SM_SIZE = (300, 300)
THUMB_SM_QUALITY = 100
THUMB_SM_SHARPEN = 1.8

THUMB_LG_SIZE = (1500, 1500)
THUMB_LG_QUALITY = 90
THUMB_LG_SHARPEN = 1.3

def make_thumbnail(image_field, size, suffix, quality, sharpen_factor=1.0):
    if not image_field:
        return None
    try:
        image_field.seek(0)
        img = Image.open(image_field)
        if img.mode not in ('L', 'RGB'):
            img = img.convert('RGB')
        
        resample_algo = getattr(Image, 'Resampling', Image)
        img.thumbnail(size, getattr(resample_algo, 'LANCZOS', getattr(Image, 'ANTIALIAS', 1)))
        
        if sharpen_factor != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpen_factor)
        
        thumb_io = io.BytesIO()
        img.save(thumb_io, format='JPEG', quality=quality)
        
        filename = os.path.basename(image_field.name)
        name, _ = os.path.splitext(filename)
        return ContentFile(thumb_io.getvalue(), name=f"{name}_{suffix}.jpg")
    except Exception:
        return None
    finally:
        image_field.seek(0)


class AircraftSubModel(models.Model):
    model = models.CharField(max_length=64, db_index=True)
    sub_model = models.CharField(max_length=64)
    usage_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["model", "sub_model"]
        constraints = [
            models.UniqueConstraint(
                fields=["model", "sub_model"],
                name="uniq_aircraft_model_sub_model",
            )
        ]

    def __str__(self) -> str:
        return f"{self.model} -> {self.sub_model}"


class Photo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1, related_name="photos")
    reg = models.CharField(max_length=32, db_index=True)
    model = models.CharField(max_length=64, db_index=True)
    airline = models.CharField(max_length=256, db_index=True)
    airport = models.CharField(max_length=256, db_index=True)
    date = models.DateField(db_index=True)
    sub_model = models.CharField(max_length=64, blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    camera = models.ForeignKey(
        "GearItem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="photos_as_camera",
        limit_choices_to={"kind": "camera"},
    )
    lens = models.ForeignKey(
        "GearItem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="photos_as_lens",
        limit_choices_to={"kind": "lens"},
    )
    src = models.URLField(max_length=500, blank=True, default="")
    image = models.ImageField(upload_to="photos/%Y/%m/", blank=True, null=True)
    image_sm = models.ImageField(upload_to="photos/%Y/%m/sm/", blank=True, null=True)
    image_lg = models.ImageField(upload_to="photos/%Y/%m/lg/", blank=True, null=True)
    featured = models.BooleanField(default=False)
    is_special_livery = models.BooleanField(default=False, verbose_name="Special Livery")
    is_cargo = models.BooleanField(default=False, verbose_name="Cargo")
    is_bizjet = models.BooleanField(default=False, verbose_name="Business Jet")
    is_helicopter = models.BooleanField(default=False, verbose_name="Helicopter")
    is_rare = models.BooleanField(default=False, verbose_name="Rare")
    def save(self, *args, **kwargs):
        if self.reg:
            self.reg = self.reg.strip().upper()
        if self.model:
            self.model = self.model.strip()
        if self.sub_model:
            self.sub_model = self.sub_model.strip()

        is_new = self.pk is None
        previous = None
        if not is_new:
            try:
                previous = Photo.objects.only("image", "model", "sub_model").get(pk=self.pk)
            except Photo.DoesNotExist:
                previous = None

        orig_image = previous.image if previous else None

        from .services import build_variant_pair, sync_variant_pair
        previous_pair = build_variant_pair(
            previous.model if previous else "",
            previous.sub_model if previous else "",
        )

        if self.image and (is_new or self.image != orig_image):
            sm_file = make_thumbnail(self.image, THUMB_SM_SIZE, "sm", THUMB_SM_QUALITY, THUMB_SM_SHARPEN)
            if sm_file:
                self.image_sm.save(sm_file.name, sm_file, save=False)
            lg_file = make_thumbnail(self.image, THUMB_LG_SIZE, "lg", THUMB_LG_QUALITY, THUMB_LG_SHARPEN)
            if lg_file:
                self.image_lg.save(lg_file.name, lg_file, save=False)

        super().save(*args, **kwargs)
        sync_variant_pair(previous_pair, build_variant_pair(self.model, self.sub_model))

    def delete(self, *args, **kwargs):
        from .services import build_variant_pair, sync_variant_pair

        current_pair = build_variant_pair(self.model, self.sub_model)
        super().delete(*args, **kwargs)
        sync_variant_pair(current_pair, None)

    class Meta:
        indexes = [
            # ✅ gallery 常见：按日期倒序（配合 order_by("-date", "-id")）
            models.Index(fields=["-date"], name="idx_photo_date_desc"),

            # ✅ 常见筛选组合 + 日期排序（减少“先筛选再排序”的成本）
            models.Index(fields=["airport", "-date"], name="idx_airport_date_desc"),
            models.Index(fields=["airline", "-date"], name="idx_airline_date_desc"),
            models.Index(fields=["model", "-date"], name="idx_model_date_desc"),
            models.Index(fields=["-date", "-id"], name="idx_date_id_desc"),
            models.Index(fields=["reg", "-date"], name="idx_reg_date_desc"),


            # ✅ 多条件同时筛时也更稳（airport+airline+model 再按 date）
            models.Index(fields=["airport", "airline", "model", "-date"], name="idx_aam_date_desc"),
        ]

    def __str__(self) -> str:
        return f"{self.reg} | {self.model} | {self.airline} | {self.airport} | {self.date}"

    @property
    def display_src(self) -> str:
        if self.image:
            return self.image.url
        return self.src

    @property
    def display_src_sm(self) -> str:
        if self.image_sm:
            try:
                return self.image_sm.url
            except ValueError:
                pass
        return self.display_src

    @property
    def display_src_lg(self) -> str:
        if self.image_lg:
            try:
                return self.image_lg.url
            except ValueError:
                pass
        return self.display_src


class SiteProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, default=1, related_name="site_profile")
    location = models.CharField(max_length=128, blank=True, default="")
    hobbies = models.CharField(max_length=256, blank=True, default="")
    avatar = models.ImageField(upload_to="site/%Y/%m/", blank=True, null=True)
    banner = models.ImageField(upload_to="site/%Y/%m/", blank=True, null=True)
    pinned_ids = models.JSONField(default=list, blank=True)
    show_perf_panel = models.BooleanField(default=False)

    def _compress_image(self, field, max_size, quality):
        """Resize and compress an ImageField to JPEG."""
        from PIL import Image
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import os

        img_file = getattr(self, field)
        if not img_file or not hasattr(img_file.file, 'read'):
            return  # no new upload

        img = Image.open(img_file)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        if isinstance(max_size, int):
            # single int → center crop to square, then resize (avatar)
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((max_size, max_size), Image.LANCZOS)
        else:
            # tuple → resize long edge (banner)
            max_edge = max_size[0]
            w, h = img.size
            if max(w, h) > max_edge:
                ratio = max_edge / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        buf.seek(0)

        name = os.path.splitext(img_file.name)[0]
        # keep only the filename part (strip any directory prefix)
        name = os.path.basename(name) + '.jpg'

        setattr(self, field, InMemoryUploadedFile(
            buf, 'ImageField', name, 'image/jpeg', buf.getbuffer().nbytes, None
        ))

    def save(self, *args, **kwargs):
        # Detect new uploads by checking if the file has a 'read' method (freshly uploaded)
        if self.avatar and hasattr(self.avatar.file, 'read'):
            self._compress_image('avatar', 128, 85)
        if self.banner and hasattr(self.banner.file, 'read'):
            self._compress_image('banner', (1920,), 80)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

class GearItem(models.Model):
    KIND_CHOICES = [("camera", "Camera"), ("lens", "Lens")]

    site = models.ForeignKey("SiteProfile", on_delete=models.CASCADE, related_name="gear")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    name = models.CharField(max_length=120)

    def __str__(self):
        return f"{self.kind}: {self.name}"
    


class PendingPhoto(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1, related_name="pending_photos")
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    reg = models.CharField(max_length=32, db_index=True)
    model = models.CharField(max_length=64, db_index=True)
    airline = models.CharField(max_length=256, db_index=True)
    airport = models.CharField(max_length=256, db_index=True)
    date = models.DateField(db_index=True)

    sub_model = models.CharField(max_length=64, blank=True, default="")
    remarks = models.TextField(blank=True, default="")

    camera = models.ForeignKey(
        "GearItem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="pending_as_camera",
        limit_choices_to={"kind": "camera"},
    )
    lens = models.ForeignKey(
        "GearItem",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="pending_as_lens",
        limit_choices_to={"kind": "lens"},
    )

    src = models.URLField(max_length=500, blank=True, default="")
    image = models.ImageField(upload_to="pending/%Y/%m/", blank=True, null=True)
    image_sm = models.ImageField(upload_to="pending/%Y/%m/sm/", blank=True, null=True)  # 缩略图，用于列表展示

    featured = models.BooleanField(default=False)
    is_special_livery = models.BooleanField(default=False, verbose_name="Special Livery")
    is_cargo = models.BooleanField(default=False, verbose_name="Cargo")
    is_bizjet = models.BooleanField(default=False, verbose_name="Business Jet")
    is_helicopter = models.BooleanField(default=False, verbose_name="Helicopter")
    is_rare = models.BooleanField(default=False, verbose_name="Rare")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)
    review_note = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(default=timezone.now, db_index=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    approved_photo = models.OneToOneField(
        "Photo",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_pending",
    )

    class Meta:
        indexes = [
            models.Index(fields=["status", "-submitted_at"], name="idx_pending_status_time"),
        ]

    def save(self, *args, **kwargs):
        if self.reg:
            self.reg = self.reg.strip().upper()
        if self.model:
            self.model = self.model.strip()
        if self.sub_model:
            self.sub_model = self.sub_model.strip()
        is_new = self.pk is None
        orig_image = None
        if not is_new:
            try:
                orig_image = PendingPhoto.objects.get(pk=self.pk).image
            except PendingPhoto.DoesNotExist:
                pass

        if self.image and (is_new or self.image != orig_image):
            sm_file = make_thumbnail(self.image, THUMB_SM_SIZE, "sm", THUMB_SM_QUALITY, THUMB_SM_SHARPEN)
            if sm_file:
                self.image_sm.save(sm_file.name, sm_file, save=False)

        super().save(*args, **kwargs)

    @property
    def display_src(self) -> str:
        if self.image:
            return self.image.url
        return self.src

    @property
    def display_src_sm(self) -> str:
        if self.image_sm:
            try:
                return self.image_sm.url
            except ValueError:
                pass
        return self.display_src
