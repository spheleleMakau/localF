from django.shortcuts import render


def home(request):
    return render(request, "agency/home.html")
