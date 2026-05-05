"""
URL configuration for planehub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from web import views as web_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # 页面
    path("login-redirect/", web_views.login_redirect, name="login_redirect"),
    path("", web_views.global_landing, name="global_landing"),
    path("<str:username>/", web_views.home, name="home"),
    path("<str:username>/gallery/", web_views.gallery, name="gallery"),
    path("<str:username>/photo/", web_views.photo, name="photo"),
    path("<str:username>/stats/", web_views.stats, name="stats"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path("", include("photos.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]
