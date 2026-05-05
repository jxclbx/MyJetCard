from __future__ import annotations

from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import ExtractYear

from ..models import Photo, SiteProfile


def photo_to_dict(p: Photo, request=None):
    def build_url(url_val):
        if url_val and request:
            return request.build_absolute_uri(url_val)
        return url_val

    src = build_url(p.display_src)
    src_sm = build_url(p.display_src_sm)
    src_lg = build_url(p.display_src_lg)

    # ✅ 新结构：Photo.camera / Photo.lens 是 FK -> GearItem
    camera_name = p.camera.name if getattr(p, "camera", None) else "Unknown Camera"
    lens_name = p.lens.name if getattr(p, "lens", None) else "Unknown Lens"

    return {
        "id": p.id,
        "reg": p.reg,
        "model": p.model,
        "sub_model": p.sub_model,
        "remarks": p.remarks,
        "airline": p.airline,
        "airport": p.airport,
        "camera_name": camera_name,
        "lens_name": lens_name,
        "src": src,
        "src_sm": src_sm,
        "src_lg": src_lg,
        "date": p.date.isoformat(),
        "featured": p.featured,
        "is_special_livery": p.is_special_livery,
        "is_cargo": p.is_cargo,
        "is_bizjet": p.is_bizjet,
        "is_helicopter": p.is_helicopter,
        "is_rare": p.is_rare,
    }


def api_photo_detail(request, username, photo_id: int):
    try:
        p = Photo.objects.get(id=photo_id, user__username=username)
    except Photo.DoesNotExist:
        raise Http404("Photo not found")
    return JsonResponse(photo_to_dict(p, request=request))


def api_photos(request, username):
    """
    GET /api/photos?airport=...&airline=...&model=...&reg=...&date=YYYY-MM-DD&featured=true
                 &ordering=-date&page=1&page_size=24
    """
    qs = Photo.objects.filter(user__username=username)

    from django.db.models import Value
    from django.db.models.functions import Replace

    for k in ["airport", "airline", "model", "date"]:
        v = request.GET.get(k)
        if v:
            qs = qs.filter(**{k: v})

    # reg: case-insensitive + ignore hyphens
    reg_val = request.GET.get("reg")
    if reg_val:
        reg_clean = reg_val.replace("-", "").upper()
        qs = qs.annotate(
            clean_reg=Replace('reg', Value('-'), Value(''))
        ).filter(clean_reg__iexact=reg_clean)

    year_val = request.GET.get("year")
    if year_val:
        qs = qs.filter(date__year=year_val)

    month_val = request.GET.get("month")
    if month_val:
        # e.g. "2026-03"
        try:
            y, m = month_val.split("-")
            qs = qs.filter(date__year=y, date__month=m)
        except ValueError:
            pass

    # Global text search (q parameter)
    q = request.GET.get("q")
    if q:
        from django.db.models import Q
        q_clean = q.replace("-", "")
        qs = qs.annotate(
            clean_reg_q=Replace('reg', Value('-'), Value(''))
        ).filter(
            Q(clean_reg_q__icontains=q_clean) |
            Q(model__icontains=q) |
            Q(sub_model__icontains=q) |
            Q(airline__icontains=q) |
            Q(airport__icontains=q) |
            Q(remarks__icontains=q)
        )

    featured = request.GET.get("featured")
    if featured is not None:
        if str(featured).lower() in ("1", "true", "yes"):
            qs = qs.filter(featured=True)
        elif str(featured).lower() in ("0", "false", "no"):
            qs = qs.filter(featured=False)

    # Boolean tag filters
    for tag_key in ["is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare"]:
        tag_val = request.GET.get(tag_key)
        if tag_val is not None and tag_val != "":
            if str(tag_val).lower() in ("1", "true", "yes"):
                qs = qs.filter(**{tag_key: True})
            elif str(tag_val).lower() in ("0", "false", "no"):
                qs = qs.filter(**{tag_key: False})

    ordering = request.GET.get("ordering", "-id")
    allowed_ordering = {"date", "-date", "id", "-id"}
    if ordering not in allowed_ordering:
        ordering = "-id"

    # ========= 新增：每个注册号只显示一张图 =========
    if request.GET.get("unique_reg") == "1":
        from django.db.models import Subquery, OuterRef
        # 子查询：选取各个 reg 在本次筛选结果中，按 date 倒序（相同时按 id 倒序）排第一的那张 id
        latest_photo_subquery = qs.filter(reg=OuterRef('reg')).order_by('-date', '-id').values('id')[:1]
        qs = qs.filter(id=Subquery(latest_photo_subquery))
    # ===============================================

    qs = qs.order_by(ordering, "-id")

    page = int(request.GET.get("page", "1"))
    page_size = int(request.GET.get("page_size", "24"))
    page_size = max(1, min(page_size, 100))

    # Calculate unique registration count for the filtered queryset
    unique_regs_count = qs.values('reg').distinct().count()

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    distinct_regs_list = []
    if request.GET.get("airline") and request.GET.get("model"):
        # 取出所有相关且独立的注册号 (必需清空 order_by 防止 id 被带入 SELECT 列导致 distinct 失效)
        raw_regs = list(qs.order_by().values_list('reg', flat=True).distinct())
        # 强制按字母表进行一次 Python 排序，确保 9V-SHA 在 9V-SJB 前面
        distinct_regs_list = sorted([str(r) for r in raw_regs if r])

    return JsonResponse({
        "count": paginator.count,
        "regs_count": unique_regs_count,
        "distinct_regs": distinct_regs_list,
        "total_pages": paginator.num_pages,
        "page": page_obj.number,
        "page_size": page_size,
        "results": [photo_to_dict(p, request=request) for p in page_obj.object_list],
    })


def api_home(request, username):
    """
    GET /api/home?latest_page=1&latest_page_size=24

    返回：
    {
      summary: {total, airlines, airports, regs},
      airports: ["SIN","PVG",...],
      pinned: [...],
      featured: [...],
      random: [...],
      charts: {
        yearly: {years:[], counts:[]},
        airline: {data:[{name,value},...]}
      }
    }
    """
    qs = Photo.objects.filter(user__username=username)

    # 1) summary
    summary = {
        "total": qs.count(),
        "airlines": qs.exclude(airline="").values("airline").distinct().count(),
        "airports": qs.exclude(airport="").values("airport").distinct().count(),
        "regs": qs.exclude(reg="").values("reg").distinct().count(),
    }

    # 2) airports distinct（给地图用）
    airports = list(
        qs.exclude(airport="")
          .values_list("airport", flat=True)
          .distinct()
          .order_by("airport")
    )

    # 3) pinned（从 SiteProfile.pinned_ids 返回 pinned）
    pinned_ids = []
    site = SiteProfile.objects.filter(user__username=username).first()
    if site and site.pinned_ids:
        pinned_ids = site.pinned_ids

    # 这里不保证顺序（如果你要按 pinned_ids 顺序展示，我也可以再改）
    pinned = [photo_to_dict(p, request=request) for p in qs.filter(id__in=pinned_ids)]

    # 4) featured 随机 8
    featured = [photo_to_dict(p, request=request) for p in qs.filter(featured=True).order_by("?")[:8]]

    # 5) random 随机 8
    random_photos = [photo_to_dict(p, request=request) for p in qs.order_by("?")[:8]]

    # 6) charts.yearly
    yearly_rows = (
        qs.annotate(year=ExtractYear("date"))
          .values("year")
          .annotate(cnt=Count("id"))
          .order_by("year")
    )
    years, counts = [], []
    for r in yearly_rows:
        y = r["year"]
        if y is None:
            continue
        years.append(str(y))
        counts.append(r["cnt"])

    # 7) charts.airline：top6 + Other
    airline_rows = list(
        qs.exclude(airline="")
          .values("airline")
          .annotate(cnt=Count("id"))
          .order_by("-cnt")
    )
    top = airline_rows[:6]
    rest = airline_rows[6:]
    other_count = sum(r["cnt"] for r in rest)

    pie_data = [{"name": r["airline"], "value": r["cnt"]} for r in top]
    if other_count > 0:
        pie_data.append({"name": "Other", "value": other_count})

    charts = {
        "yearly": {"years": years, "counts": counts},
        "airline": {"data": pie_data},
    }

    return JsonResponse({
        "summary": summary,
        "airports": airports,
        "pinned": pinned,
        "featured": featured,
        "random": random_photos,
        "charts": charts,
    })
