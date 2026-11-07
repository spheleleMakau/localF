from django.shortcuts import render
from camp.views import apply


def home(request):
    return render(request, "agency/home.html")


def join(request):
    return apply(request)
