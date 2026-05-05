import json
import os
import re
from collections import Counter, defaultdict

from django.core.files.base import ContentFile
from django.utils import timezone

from .models import AircraftSubModel, PendingPhoto, Photo


# ── Airport data ──────────────────────────────────────────────────────────────

_AIRPORT_DATA = None

def get_airport_data():
    # 无入参；返回：{IATA码: {"ic": ICAO码, ...}} 字典，文件缺失或解析失败时返回 {}
    # 被 forms.py 的 clean_airport() 调用，用于校验用户输入的机场代码并将 ICAO 自动转换为 IATA
    # 结果缓存在模块级变量 _AIRPORT_DATA，进程内只读一次文件
    global _AIRPORT_DATA
    if _AIRPORT_DATA is None:
        try:
            from django.conf import settings
            config_path = os.path.join(settings.BASE_DIR, 'static', 'airport-data.js')
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            match = re.search(r'const\s+AIRPORT_DATA\s*=\s*(.*?);', content, re.DOTALL)
            _AIRPORT_DATA = json.loads(match.group(1)) if match else {}
        except Exception:
            _AIRPORT_DATA = {}
    return _AIRPORT_DATA


# ── Aircraft variant helpers ──────────────────────────────────────────────────

def normalize_aircraft_text(value):
    # 入参：任意字符串或 None；返回：去除首尾空格的字符串，None 转为 ""
    # 被 build_variant_pair / get_model_choices 调用，确保写入 AircraftSubModel 前数据一致
    return (value or "").strip()


def build_variant_pair(model, sub_model):
    # 入参：model 和 sub_model 原始字符串；返回：标准化后的 (model, sub_model) 元组，任一为空则返回 None
    # 被 Photo.save() / Photo.delete() 调用，用于构造传给 sync_variant_pair 的参数
    model = normalize_aircraft_text(model)
    sub_model = normalize_aircraft_text(sub_model)
    if not model or not sub_model:
        return None
    return model, sub_model


def sync_variant_pair(previous_pair, current_pair):
    # 入参：修改前的 pair（或 None）、修改后的 pair（或 None）；无返回值
    # 被 Photo.save() / Photo.delete() 调用：保存时传 (旧pair, 新pair)，删除时传 (当前pair, None)
    # 两者相同表示机型未变，直接跳过，避免无效写库
    if previous_pair == current_pair:
        return
    if previous_pair:
        decrement_variant(*previous_pair)
    if current_pair:
        increment_variant(*current_pair)


def increment_variant(model, sub_model):
    # 入参：model 和 sub_model 字符串；无返回值
    # 被 sync_variant_pair 调用，新增一张照片后将对应 AircraftSubModel.usage_count +1，记录不存在则创建
    variant, created = AircraftSubModel.objects.get_or_create(
        model=model,
        sub_model=sub_model,
        defaults={"usage_count": 1},
    )
    if not created:
        variant.usage_count += 1
        variant.save(update_fields=["usage_count", "updated_at"])


def decrement_variant(model, sub_model):
    # 入参：model 和 sub_model 字符串；无返回值
    # 被 sync_variant_pair 调用，删除或修改一张照片后将对应 AircraftSubModel.usage_count -1
    # usage_count 降到 0 时删除该行，防止前端下拉出现无照片的机型选项
    try:
        variant = AircraftSubModel.objects.get(model=model, sub_model=sub_model)
    except AircraftSubModel.DoesNotExist:
        return

    if variant.usage_count <= 1:
        variant.delete()
        return

    variant.usage_count -= 1
    variant.save(update_fields=["usage_count", "updated_at"])


def rebuild_aircraft_variants():
    # 无入参；无返回值
    # 被管理命令 sync_aircraft_submodels 调用，用于数据修复或初始化场景
    # 全表扫描 Photo 重新统计各 (model, sub_model) 的出现次数，整表替换 AircraftSubModel
    counts = Counter()
    for model, sub_model in Photo.objects.values_list("model", "sub_model").iterator():
        pair = build_variant_pair(model, sub_model)
        if pair:
            counts[pair] += 1

    AircraftSubModel.objects.all().delete()
    AircraftSubModel.objects.bulk_create(
        [
            AircraftSubModel(model=model, sub_model=sub_model, usage_count=count)
            for (model, sub_model), count in sorted(counts.items())
        ]
    )


def get_model_submodel_map():
    # 无入参；返回：{model: [sub_model, ...]} 字典，sub_model 列表按字母排序
    # 被照片新增/编辑页面的 view 调用，序列化为 JSON 后注入模板，驱动前端机型-子型号联动下拉
    mapping = defaultdict(list)
    for model, sub_model in AircraftSubModel.objects.values_list(
        "model", "sub_model"
    ).order_by("model", "sub_model"):
        mapping[model].append(sub_model)
    return dict(mapping)


def get_model_choices():
    # 无入参；返回：Photo 表中所有非空 model 值的去重排序列表
    # 被照片新增/编辑页面的 view 调用，用于填充机型主下拉框的候选项
    values = set()
    for model in Photo.objects.values_list("model", flat=True).iterator():
        model = normalize_aircraft_text(model)
        if model:
            values.add(model)
    return sorted(values)


# ── Review services ───────────────────────────────────────────────────────────

def approve_pending(p: PendingPhoto) -> Photo:
    # 入参：一个 status="pending" 的 PendingPhoto 实例；返回：新建的 Photo 实例
    # 被 api/api_review.py 的审核通过接口调用
    # 将 pending 的元数据和原图复制到正式 Photo，Photo.save() 内部自动生成 image_sm / image_lg
    # PendingPhoto.image 字段置空（引用清除，物理文件保留），image_sm 保留供历史列表展示
    photo = Photo.objects.create(
        user=p.user,
        reg=p.reg,
        model=p.model,
        airline=p.airline,
        airport=p.airport,
        date=p.date,
        sub_model=p.sub_model,
        remarks=p.remarks,
        camera=p.camera,
        lens=p.lens,
        src=p.src,
        featured=p.featured,
        is_special_livery=p.is_special_livery,
        is_cargo=p.is_cargo,
        is_bizjet=p.is_bizjet,
        is_helicopter=p.is_helicopter,
        is_rare=p.is_rare,
    )

    original_sm_name = p.image_sm.name if p.image_sm else ""

    if p.image:
        fname = os.path.basename(p.image.name)
        p.image.seek(0)
        content = p.image.read()
        p.image.close()
        photo.image.save(fname, ContentFile(content), save=True)

    # 用 update() 写库，绕过 PendingPhoto.save() 避免重复生成缩略图
    PendingPhoto.objects.filter(pk=p.pk).update(
        status="approved",
        reviewed_at=timezone.now(),
        image="",
        image_sm=original_sm_name,
        approved_photo_id=photo.id,
    )

    p.refresh_from_db()
    return photo


def reject_pending(p: PendingPhoto, note: str = "") -> None:
    # 入参：一个 status="pending" 的 PendingPhoto 实例，note 为可选的拒绝原因文字；无返回值
    # 被 api/api_review.py 的审核拒绝接口调用
    # 将 status 改为 rejected 并记录拒绝原因，PendingPhoto.image 置空，image_sm 保留，物理文件不删
    PendingPhoto.objects.filter(pk=p.pk).update(
        status="rejected",
        review_note=note or "",
        reviewed_at=timezone.now(),
        image="",
    )
