from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

def global_landing(request):
    return render(request, "global_landing.html")

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def login_redirect(request):
    # Redirect logged in users to their personal home/dashboard
    return redirect("home", username=request.user.username)

def home(request, username):
    view_user = get_object_or_404(User, username=username)
    return render(request, "home.html", {"view_user": view_user})

def gallery(request, username):
    view_user = get_object_or_404(User, username=username)
    return render(request, "gallery.html", {"view_user": view_user})

def photo(request, username):
    view_user = get_object_or_404(User, username=username)
    return render(request, "photo_page_detailed.html", {"view_user": view_user})

def stats(request, username):
    view_user = get_object_or_404(User, username=username)
    return render(request, "stats.html", {"view_user": view_user})

