from django.shortcuts import render
from camp.views import apply


def home(request):
    return render(request, "agency/home.html")


def join(request):
    return apply(request)


def models_gallery(request):
    return render(request, "agency/models_gallery.html")


def entertainers_gallery(request):
    return render(request, "agency/entertainers_gallery.html")


def founder_portfolio(request):
    return render(request, "agency/founder_portfolio.html")
