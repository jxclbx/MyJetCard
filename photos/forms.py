from django import forms
from .models import Photo, GearItem, SiteProfile, PendingPhoto
from .services import get_airport_data

class PhotoCreateForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = [
            "image",
            "reg", "model", "sub_model",
            "airline", "airport", "date",
            "camera", "lens",
            "remarks", "featured",
            "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "airline": forms.TextInput(attrs={"autocomplete": "off"}),
            "model": forms.TextInput(attrs={"autocomplete": "off"}),
            "sub_model": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, site: SiteProfile = None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = GearItem.objects.all()
        if site is not None:
            qs = qs.filter(site=site)
        self.fields["camera"].queryset = qs.filter(kind="camera").order_by("id")
        self.fields["lens"].queryset = qs.filter(kind="lens").order_by("id")

    # clean_ 方法用于对单个字段进行清洗，这里对注册号进行清洗，去除空格并转换为大写
    def clean_reg(self):
        val = self.cleaned_data.get("reg")
        if val:
            return val.strip().upper()
        return val

    # clean_ 方法用于对单个字段进行清洗，这里对图片进行清洗，去除空格并转换为大写，如果图片不合法，则抛出异常
    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            if image.size > 3 * 1024 * 1024:
                raise forms.ValidationError(f"Image size exceeds 3MB, current size is {image.size / (1024**2):.1f}MB")
            try:
                from PIL import Image
                img = Image.open(image)
                if img.format not in ["JPEG", "PNG", "WEBP"]:
                    raise forms.ValidationError("Only JPG and PNG images are allowed.")
                width, height = img.size
                image.seek(0)
                max_edge = max(width, height)
                if max_edge > 2560:
                    raise forms.ValidationError(f"Image edge length cannot exceed 2560px, current image size is {width}x{height}.")
            except forms.ValidationError as e:
                raise e
            except Exception:
                pass
        return image

    # clean_ 方法用于对单个字段进行清洗，这里对机场进行清洗，去除空格并转换为大写，如果机场代码不合法，则抛出异常
    def clean_airport(self):
        val = self.cleaned_data.get("airport", "").strip().upper()
        if not val:
            return val
        data = get_airport_data()
        if len(val) == 3 and val in data:
            return val
        if len(val) == 4:
            for iata, info in data.items():
                if info.get("ic", "").upper() == val:
                    return iata
        return val


class PhotoEditForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = [
            "reg", "model", "sub_model",
            "airline", "airport", "date",
            "camera", "lens",
            "remarks", "featured",
            "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "airline": forms.TextInput(attrs={"autocomplete": "off"}),
            "model": forms.TextInput(attrs={"autocomplete": "off"}),
            "sub_model": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, site: SiteProfile = None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = GearItem.objects.all()
        if site is not None:
            qs = qs.filter(site=site)
        self.fields["camera"].queryset = qs.filter(kind="camera").order_by("id")
        self.fields["lens"].queryset = qs.filter(kind="lens").order_by("id")

    # clean_ 方法用于对单个字段进行清洗，这里对注册号进行清洗，去除空格并转换为大写
    def clean_reg(self):
        val = self.cleaned_data.get("reg")
        if val:
            return val.strip().upper()
        return val

    # clean_ 方法用于对单个字段进行清洗，这里对机场进行清洗，去除空格并转换为大写，如果机场代码不合法，则抛出异常
    def clean_airport(self):
        val = self.cleaned_data.get("airport", "").strip().upper()
        if not val:
            return val
        data = get_airport_data()
        if len(val) == 3 and val in data:
            return val
        if len(val) == 4:
            for iata, info in data.items():
                if info.get("ic", "").upper() == val:
                    return iata
        return val


class SiteProfileForm(forms.ModelForm):
    class Meta:
        model = SiteProfile
        fields = ["location", "hobbies", "avatar", "banner", "pinned_ids", "show_perf_panel"]
        widgets = {
            "hobbies": forms.TextInput(),
            "pinned_ids": forms.Textarea(attrs={"rows": 3}),
        }

    # clean_ 方法用于对单个字段进行清洗，这里对pinned_ids进行清洗，去除空格并转换为列表
    def clean_pinned_ids(self):
        v = self.cleaned_data.get("pinned_ids")
        if isinstance(v, str):
            import json
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
            except Exception:
                raise forms.ValidationError("pinned_ids must be a valid JSON, like [1, 2, 3]")
            if not isinstance(parsed, list):
                raise forms.ValidationError("pinned_ids must be an array, like [1, 2, 3]")
            return parsed
        return v


class GearItemForm(forms.ModelForm):
    class Meta:
        model = GearItem
        fields = ["kind", "name"]


class PendingPhotoCreateForm(forms.ModelForm):
    class Meta:
        model = PendingPhoto
        fields = [
            "image",
            "reg", "model", "sub_model",
            "airline", "airport", "date",
            "camera", "lens",
            "remarks", "featured",
            "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "airline": forms.TextInput(attrs={"autocomplete": "off"}),
            "model": forms.TextInput(attrs={"autocomplete": "off"}),
            "sub_model": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, site: SiteProfile = None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = GearItem.objects.all()
        if site is not None:
            qs = qs.filter(site=site)
        self.fields["camera"].queryset = qs.filter(kind="camera").order_by("id")
        self.fields["lens"].queryset = qs.filter(kind="lens").order_by("id")

    def clean_reg(self):
        val = self.cleaned_data.get("reg")
        if val:
            return val.strip().upper()
        return val

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            if image.size > 3 * 1024 * 1024:
                raise forms.ValidationError(f"Image size exceeds 3MB, current size is {image.size / (1024**2):.1f}MB")
            try:
                from PIL import Image
                img = Image.open(image)
                if img.format not in ["JPEG", "PNG", "WEBP"]:
                    raise forms.ValidationError("Only JPG and PNG images are allowed.")
                width, height = img.size
                image.seek(0)
                max_edge = max(width, height)
                if max_edge > 2560:
                    raise forms.ValidationError(f"Image edge length cannot exceed 2560px, current image size is {width}x{height}.")
            except forms.ValidationError as e:
                raise e
            except Exception:
                pass
        return image

    def clean_airport(self):
        val = self.cleaned_data.get("airport", "").strip().upper()
        if not val:
            return val
        data = get_airport_data()
        if len(val) == 3 and val in data:
            return val
        if len(val) == 4:
            for iata, info in data.items():
                if info.get("ic", "").upper() == val:
                    return iata
        return val

    def clean(self):
        cleaned = super().clean()
        image = cleaned.get("image")
        if not image:
            raise forms.ValidationError("Must upload an image.")
        return cleaned


class PendingPhotoEditForm(forms.ModelForm):
    class Meta:
        model = PendingPhoto
        fields = [
            "reg", "model", "sub_model",
            "airline", "airport", "date",
            "camera", "lens",
            "remarks", "featured",
            "is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
            "airline": forms.TextInput(attrs={"autocomplete": "off"}),
            "model": forms.TextInput(attrs={"autocomplete": "off"}),
            "sub_model": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, site: SiteProfile = None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = GearItem.objects.all()
        if site is not None:
            qs = qs.filter(site=site)
        self.fields["camera"].queryset = qs.filter(kind="camera").order_by("id")
        self.fields["lens"].queryset = qs.filter(kind="lens").order_by("id")
    
    # clean_ 方法用于对单个字段进行清洗，这里对注册号进行清洗，去除空格并转换为大写
    def clean_reg(self):
        val = self.cleaned_data.get("reg")
        if val:
            return val.strip().upper()
        return val

    # clean_ 方法用于对单个字段进行清洗，这里对机场进行清洗，去除空格并转换为大写，如果机场代码不合法，则抛出异常
    def clean_airport(self):
        val = self.cleaned_data.get("airport", "").strip().upper()
        if not val:
            return val
        data = get_airport_data()
        if len(val) == 3 and val in data:
            return val
        if len(val) == 4:
            for iata, info in data.items():
                if info.get("ic", "").upper() == val:
                    return iata
        return val
