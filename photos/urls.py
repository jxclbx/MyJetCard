from django.urls import path

from .views.view_photos import (
    manage_photo_list,
    manage_photo_add,
    manage_photo_edit,
    manage_photo_delete,
    manage_photo_replace_image,
)
from .views.view_pending import (
    manage_pending_list,
    manage_pending_edit,
    submit_pending_page,
    review_queue_page,
)
from .views.view_site_profile import manage_site, manage_gear_edit, manage_gear_delete
from .api.api_photos import api_home, api_photos, api_photo_detail
from .api.api_stats import api_stats_overview, api_stats_year, api_stats_regs
from .api.api_site import api_site
from .api import api_review

urlpatterns = [
    # Photo CRUD
    path("manage/photos/",                              manage_photo_list,        name="photos_manage_list"),
    path("manage/photos/add-direct/",                  manage_photo_add,         name="photos_manage_add"),
    path("manage/photos/<int:photo_id>/edit/",          manage_photo_edit,        name="photos_manage_edit"),
    path("manage/photos/<int:photo_id>/delete/",        manage_photo_delete,      name="photos_manage_delete"),
    path("manage/photos/<int:photo_id>/replace/",       manage_photo_replace_image, name="photos_manage_replace_image"),

    # Pending photos
    path("manage/photos/pending/",                      manage_pending_list,      name="photos_manage_pending_list"),
    path("manage/photos/pending/<int:pending_id>/edit/", manage_pending_edit,     name="photos_manage_pending_edit"),
    path("manage/photos/add/",                          submit_pending_page,      name="submit_pending"),
    path("manage/review/",                              review_queue_page,        name="review_queue"),

    # Site profile & gear
    path("manage/site/",                                manage_site,              name="photos_manage_site"),
    path("manage/gear/<int:gear_id>/edit/",             manage_gear_edit,         name="photos_manage_gear_edit"),
    path("manage/gear/<int:gear_id>/delete/",           manage_gear_delete,       name="photos_manage_gear_delete"),

    # APIs - photos
    path("api/<str:username>/home",                     api_home),
    path("api/<str:username>/photos",                   api_photos),
    path("api/<str:username>/photos/<int:photo_id>/",   api_photo_detail),

    # APIs - stats
    path("api/<str:username>/stats/overview/",          api_stats_overview),
    path("api/<str:username>/stats/year/",              api_stats_year),
    path("api/<str:username>/stats/regs/",              api_stats_regs),

    # APIs - site & review
    path("api/<str:username>/site/",                    api_site,                 name="api_site"),
    path("api/pending/",                                api_review.pending_list,  name="api_pending_list"),
    path("api/pending/<int:pk>/approve/",               api_review.pending_approve, name="api_pending_approve"),
    path("api/pending/<int:pk>/reject/",                api_review.pending_reject,  name="api_pending_reject"),
]
