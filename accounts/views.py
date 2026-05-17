import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect

def login_view(request):
    if request.method == "POST":

        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({"message": "JSON inválido"}, status=400)

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"message": "Campos requeridos"}, status=400)

        user = authenticate(request, username=username, password=password)

        if user is None:
            return JsonResponse({"message": "Credenciales incorrectas"}, status=401)

        if not user.is_active:
            return JsonResponse({"message": "Usuario inactivo"}, status=403)

        login(request, user)

        if user.groups.filter(name="cajeros").exists():
            groups=2
        else:
            groups=1

        return JsonResponse({
            "message": "Login exitoso",
            "username": user.username,
            "groups": groups
        })

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")