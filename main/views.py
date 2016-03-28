from django.shortcuts import render

def viewer(request):
    return render(request, 'main.html')