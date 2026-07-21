from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

def inicio(request):
    return render(request, "index.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        usuario = request.POST.get("username", "").strip()
        clave = request.POST.get("password", "").strip()

        if not usuario or not clave:
            messages.error(request, "Por favor, ingresa tu usuario y contraseña.")
        else:
            user = authenticate(request, username=usuario, password=clave)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido de nuevo, {user.username}!")
                return redirect("inicio")
            else:
                messages.error(request, "Usuario o contraseña incorrectos. Por favor, verifica tus datos.")

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect("inicio")

def register_view(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        usuario = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        clave1 = request.POST.get("password", "").strip()
        clave2 = request.POST.get("password_confirm", "").strip()

        if not usuario or not clave1:
            messages.error(request, "El nombre de usuario y la contraseña son obligatorios.")
        elif clave1 != clave2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(username=usuario).exists():
            messages.error(request, "El nombre de usuario ya está registrado.")
        else:
            user = User.objects.create_user(username=usuario, email=email, password=clave1)
            login(request, user)
            messages.success(request, f"Cuenta creada con éxito. ¡Bienvenido {user.username}!")
            return redirect("inicio")

    return render(request, "registro.html")