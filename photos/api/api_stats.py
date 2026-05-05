from __future__ import annotations

from datetime import date as date_cls
from collections import defaultdict

from django.http import JsonResponse
from django.db.models import Count, Q
from django.db.models.functions import ExtractYear, ExtractMonth


from ..models import Photo


def _apply_filters(qs, params):
    """
    只支持等值过滤：airline/airport/model/reg/date + featured
    和你前端 gallery 逻辑保持一致
    """
    for k in ["airline", "airport", "model", "reg", "date"]:
        v = params.get(k)
        if v:
            qs = qs.filter(**{k: v})

    featured = params.get("featured")
    if featured is not None and featured != "":
        if str(featured).lower() in ("1", "true", "yes"):
            qs = qs.filter(featured=True)
        elif str(featured).lower() in ("0", "false", "no"):
            qs = qs.filter(featured=False)

    # Boolean tag filters
    for tag_key in ["is_special_livery", "is_cargo", "is_bizjet", "is_helicopter", "is_rare"]:
        tag_val = params.get(tag_key)
        if tag_val is not None and tag_val != "":
            if str(tag_val).lower() in ("1", "true", "yes"):
                qs = qs.filter(**{tag_key: True})
            elif str(tag_val).lower() in ("0", "false", "no"):
                qs = qs.filter(**{tag_key: False})

    return qs


def api_stats_overview(request, username):
    qs = Photo.objects.filter(user__username=username)

    # 1) years + yearly_counts
    yearly_rows = (
        qs.annotate(year=ExtractYear("date"))
          .values("year")
          .annotate(cnt=Count("id"))
          .order_by("year")
    )

    years = []
    yearly_counts = {}
    for r in yearly_rows:
        y = r["year"]
        if y is None:
            continue
        ys = str(y)
        years.append(ys)
        yearly_counts[ys] = r["cnt"]

    latest_year = years[-1] if years else None

    # 2) 排行榜：airline / model / airport
    def ranked(field: str, top_n: int = 50):
        rows = (
            qs.exclude(**{f"{field}": ""})
              .values(field)
              .annotate(cnt=Count("id"))
              .order_by("-cnt")[:top_n]
        )
        return [{"name": r[field], "value": r["cnt"]} for r in rows]

    ranked_airline = ranked("airline")
    ranked_model = ranked("model")
    ranked_airport = ranked("airport")

    # 3) filters 下拉：唯一值列表（给 stats 页筛选用）
    airlines = list(qs.exclude(airline="").values_list("airline", flat=True).distinct().order_by("airline"))
    airports = list(qs.exclude(airport="").values_list("airport", flat=True).distinct().order_by("airport"))
    models = list(qs.exclude(model="").values_list("model", flat=True).distinct().order_by("model"))

    return JsonResponse({
        "years": years,
        "latest_year": latest_year,
        "yearly_counts": yearly_counts,
        "ranked": {
            "airline": ranked_airline,
            "model": ranked_model,
            "airport": ranked_airport,
        },
        "filters": {
            "airlines": airlines,
            "airports": airports,
            "models": models,
        }
    })


def api_stats_year(request, username):
    year_str = request.GET.get("year")
    if not year_str:
        return JsonResponse({"error": "year is required"}, status=400)

    try:
        year_int = int(year_str)
    except ValueError:
        return JsonResponse({"error": "year must be int"}, status=400)

    qs = Photo.objects.filter(user__username=username, date__year=year_int)

    # 1) monthly_counts
    monthly_rows = (
        qs.annotate(m=ExtractMonth("date"))
          .values("m")
          .annotate(cnt=Count("id"))
          .order_by("m")
    )
    monthly_counts = [0] * 12
    for r in monthly_rows:
        m = r["m"]
        if m is None:
            continue
        monthly_counts[int(m) - 1] = r["cnt"]

    # 2) heatmap: 按日期聚合（YYYY-MM-DD -> count）
    day_rows = (
        qs.values("date")
          .annotate(cnt=Count("id"))
          .order_by("date")
    )
    heatmap = []
    heatmap_max = 0
    for r in day_rows:
        d = r["date"]
        c = r["cnt"]
        if d is None:
            continue
        heatmap.append([d.isoformat(), c])
        if c > heatmap_max:
            heatmap_max = c

    return JsonResponse({
        "monthly_counts": monthly_counts,
        "heatmap": heatmap,
        "heatmap_max": heatmap_max if heatmap_max > 0 else 5
    })


# deprecated
def api_stats_regs(request, username):
    """
    GET /api/stats/regs/?airline=...&airport=...&model=...&featured=true
    return：{ regs: [...] }
    """
    qs = Photo.objects.filter(user__username=username)
    qs = _apply_filters(qs, request.GET)

    regs = list(
        qs.exclude(reg="")
          .values_list("reg", flat=True)
          .distinct()
    )

    return JsonResponse({"regs": regs})
