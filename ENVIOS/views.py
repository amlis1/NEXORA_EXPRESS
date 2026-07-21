from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from .models import UserProfile, Envio


def inicio(request):
    tracking_query = request.GET.get("tracking", "").strip()
    if tracking_query:
        return redirect("rastrear_envio_codigo", tracking_code=tracking_query)
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
    if not hasattr(request.user, 'profile') or request.user.profile.role not in ['cliente', 'admin']:
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    if request.method == "POST":
        origen = request.POST.get("origen", "Latacunga").strip() or "Latacunga"
        oficina = request.POST.get("oficina", "Oficina Central Latacunga").strip() or "Oficina Central Latacunga"
        transporte = request.POST.get("transporte", "Camión Exprés 01").strip() or "Camión Exprés 01"
        
        nombre_remitente = request.POST.get("nombre_remitente", "").strip()
        telefono_remitente = request.POST.get("telefono_remitente", "").strip()
        direccion_remitente = request.POST.get("direccion_remitente", "").strip()
        
        ciudad_destino = request.POST.get("ciudad_destino", "Quito").strip() or "Quito"
        nombre_destinatario = request.POST.get("nombre_destinatario", "").strip()
        telefono_destinatario = request.POST.get("telefono_destinatario", "").strip()
        direccion_destinatario = request.POST.get("direccion_destinatario", "").strip()
        correo_destinatario = request.POST.get("correo_destinatario", "").strip()
        
        descripcion = request.POST.get("descripcion", "").strip()
        peso = request.POST.get("peso", "").strip()
        dimensiones = request.POST.get("dimensiones", "").strip()
        costo = request.POST.get("costo", "0").strip()
        eta_raw = request.POST.get("hora_estimada_llegada", "").strip()

        if not all([nombre_remitente, telefono_remitente, direccion_remitente,
                    ciudad_destino, nombre_destinatario, telefono_destinatario, direccion_destinatario,
                    descripcion, peso]):
            messages.error(request, "Por favor, completa todos los campos obligatorios.")
        else:
            try:
                eta = None
                if eta_raw:
                    try:
                        eta = datetime.strptime(eta_raw, "%Y-%m-%dT%H:%M")
                    except ValueError:
                        pass

                envio = Envio.objects.create(
                    remitente=request.user,
                    origen=origen,
                    oficina=oficina,
                    transporte=transporte,
                    nombre_remitente=nombre_remitente,
                    telefono_remitente=telefono_remitente,
                    direccion_remitente=direccion_remitente,
                    ciudad_destino=ciudad_destino,
                    nombre_destinatario=nombre_destinatario,
                    telefono_destinatario=telefono_destinatario,
                    direccion_destinatario=direccion_destinatario,
                    correo_destinatario=correo_destinatario,
                    descripcion=descripcion,
                    peso=peso,
                    dimensiones=dimensiones,
                    costo=costo or 0,
                    hora_estimada_llegada=eta,
                    ubicacion_actual=f"Recepcionado en {oficina} ({origen})",
                )
                messages.success(request, f"Encomienda registrada con éxito. Código Tracking: {envio.numero_tracking}")
                if request.user.profile.role == 'admin':
                    return redirect("admin_envios")
                return redirect("mis_envios")
            except Exception as e:
                messages.error(request, f"Error al registrar la encomienda: {str(e)}")

    return render(request, "crear_envio.html")


@login_required
def mis_envios(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'cliente':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    envios = Envio.objects.filter(remitente=request.user)
    return render(request, "mis_envios.html", {"envios": envios})


@login_required
def rastrear_envio(request, tracking_code=None):
    if not tracking_code:
        tracking_code = request.GET.get("tracking", "").strip()

    if not tracking_code:
        messages.warning(request, "Por favor ingresa un código de tracking para rastrear.")
        return redirect("inicio")

    envio = Envio.objects.filter(numero_tracking__iexact=tracking_code).first()

    if not envio:
        messages.error(request, f"No se encontró ninguna encomienda con el código '{tracking_code}'.")
        return redirect("inicio")

    # REGLA DE CONFIDENCIALIDAD: Solo el remitente (dueño) o el admin pueden ver el paquete
    is_owner = (request.user == envio.remitente)
    is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

    if not (is_owner or is_admin):
        messages.error(request, "⛔ ACCESO DENEGADO POR SEGURIDAD Y CONFIDENCIALIDAD: Solo el cliente propietario del envío o el Administrador pueden consultar la ubicación de esta encomienda.")
        return redirect("inicio")

    return render(request, "rastrear_envio.html", {"envio": envio, "is_owner": is_owner, "is_admin": is_admin})


@login_required
def admin_envios(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect("inicio")

    envios = Envio.objects.all()
    estado_filtro = request.GET.get("estado", "")
    if estado_filtro:
        envios = envios.filter(estado=estado_filtro)

    # Métricas y Reportes del Mes Actual
    now = timezone.now()
    recaudado_mes = Envio.objects.filter(
        fecha_creacion__year=now.year,
        fecha_creacion__month=now.month
    ).aggregate(Sum('costo'))['costo__sum'] or 0

    total_pendientes = Envio.objects.filter(estado='pendiente').count()
    total_transito = Envio.objects.filter(estado='en_transito').count()
    total_entregados = Envio.objects.filter(estado='entregado').count()
    total_cancelados = Envio.objects.filter(estado='cancelado').count()

    context = {
        "envios": envios,
        "estado_filtro": estado_filtro,
        "recaudado_mes": recaudado_mes,
        "total_pendientes": total_pendientes,
        "total_transito": total_transito,
        "total_entregados": total_entregados,
        "total_cancelados": total_cancelados,
        "mes_actual": now.strftime("%B %Y"),
    }
    return render(request, "admin_envios.html", context)


@login_required
def admin_actualizar_envio(request, envio_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("inicio")

    envio = get_object_or_404(Envio, id=envio_id)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado", "")
        ubicacion_actual = request.POST.get("ubicacion_actual", "").strip()
        transporte = request.POST.get("transporte", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        eta_raw = request.POST.get("hora_estimada_llegada", "").strip()

        if nuevo_estado in dict(Envio.ESTADO_CHOICES):
            envio.estado = nuevo_estado
            if ubicacion_actual:
                envio.ubicacion_actual = ubicacion_actual
            if transporte:
                envio.transporte = transporte
            if observaciones:
                envio.observaciones = observaciones
            
            if eta_raw:
                try:
                    envio.hora_estimada_llegada = datetime.strptime(eta_raw, "%Y-%m-%dT%H:%M")
                except ValueError:
                    pass

            if nuevo_estado == 'entregado':
                envio.ubicacion_actual = f"Entregado con éxito en {envio.ciudad_destino} ({envio.direccion_destinatario})"

            envio.save()
            messages.success(request, f"Estado de encomienda {envio.numero_tracking} actualizado a '{envio.get_estado_display()}'.")
        else:
            messages.error(request, "Estado no válido.")

        return redirect("admin_envios")

    return render(request, "admin_actualizar_envio.html", {"envio": envio})

