from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile, Envio


def inicio(request):
    return render(request, "index.html")


def _redirect_by_role(user):
    if hasattr(user, 'profile') and user.profile.role == 'admin':
        return redirect("admin_envios")
    return redirect("inicio")


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

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
                return _redirect_by_role(user)
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
        telefono = request.POST.get("telefono", "").strip()
        direccion = request.POST.get("direccion", "").strip()

        if not usuario or not clave1:
            messages.error(request, "El nombre de usuario y la contraseña son obligatorios.")
        elif clave1 != clave2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(username=usuario).exists():
            messages.error(request, "El nombre de usuario ya está registrado.")
        else:
            user = User.objects.create_user(username=usuario, email=email, password=clave1)
            UserProfile.objects.create(user=user, role='cliente', telefono=telefono, direccion=direccion)
            login(request, user)
            messages.success(request, f"Cuenta creada con éxito. ¡Bienvenido {user.username}!")
            return redirect("inicio")

    return render(request, "registro.html")


@login_required
def crear_envio(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'cliente':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    if request.method == "POST":
        nombre_remitente = request.POST.get("nombre_remitente", "").strip()
        telefono_remitente = request.POST.get("telefono_remitente", "").strip()
        direccion_remitente = request.POST.get("direccion_remitente", "").strip()
        nombre_destinatario = request.POST.get("nombre_destinatario", "").strip()
        telefono_destinatario = request.POST.get("telefono_destinatario", "").strip()
        direccion_destinatario = request.POST.get("direccion_destinatario", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        peso = request.POST.get("peso", "").strip()
        dimensiones = request.POST.get("dimensiones", "").strip()
        costo = request.POST.get("costo", "0").strip()

        if not all([nombre_remitente, telefono_remitente, direccion_remitente,
                    nombre_destinatario, telefono_destinatario, direccion_destinatario,
                    descripcion, peso]):
            messages.error(request, "Por favor, completa todos los campos obligatorios.")
        else:
            try:
                envio = Envio.objects.create(
                    remitente=request.user,
                    nombre_remitente=nombre_remitente,
                    telefono_remitente=telefono_remitente,
                    direccion_remitente=direccion_remitente,
                    nombre_destinatario=nombre_destinatario,
                    telefono_destinatario=telefono_destinatario,
                    direccion_destinatario=direccion_destinatario,
                    descripcion=descripcion,
                    peso=peso,
                    dimensiones=dimensiones,
                    costo=costo or 0,
                )
                messages.success(request, f"Envío creado exitosamente. Tracking: {envio.numero_tracking}")
                return redirect("mis_envios")
            except Exception as e:
                messages.error(request, f"Error al crear el envío: {str(e)}")

    return render(request, "crear_envio.html")


@login_required
def mis_envios(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'cliente':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    envios = Envio.objects.filter(remitente=request.user)
    return render(request, "mis_envios.html", {"envios": envios})


@login_required
def admin_envios(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("inicio")

    envios = Envio.objects.all()
    estado_filtro = request.GET.get("estado", "")
    if estado_filtro:
        envios = envios.filter(estado=estado_filtro)

    return render(request, "admin_envios.html", {"envios": envios, "estado_filtro": estado_filtro})


@login_required
def admin_actualizar_envio(request, envio_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    envio = get_object_or_404(Envio, id=envio_id)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado", "")
        observaciones = request.POST.get("observaciones", "").strip()

        if nuevo_estado in dict(Envio.ESTADO_CHOICES):
            envio.estado = nuevo_estado
            envio.observaciones = observaciones
            envio.save()
            messages.success(request, f"Envío {envio.numero_tracking} actualizado correctamente.")
        else:
            messages.error(request, "Estado no válido.")

        return redirect("admin_envios")

    return render(request, "admin_actualizar_envio.html", {"envio": envio})
