from django.shortcuts import render


def home(request):
    return render(request, "agency/home.html")


def join(request):
    return render(request, "agency/join.html")
