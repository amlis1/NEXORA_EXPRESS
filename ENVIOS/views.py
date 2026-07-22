from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.conf import settings
from django.core.mail import EmailMessage
from xhtml2pdf import pisa
from .models import UserProfile, Envio
import base64
import qrcode
from io import BytesIO


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
                display_name = user.profile.get_display_name() if hasattr(user, 'profile') else user.username
                messages.success(request, f"¡Bienvenido de nuevo, {display_name}!")
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
        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        usuario = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        clave1 = request.POST.get("password", "").strip()
        clave2 = request.POST.get("password_confirm", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        direccion = request.POST.get("direccion", "").strip()

        if not usuario or not clave1 or not nombres or not apellidos:
            messages.error(request, "Nombres, apellidos, usuario y contraseña son obligatorios.")
        elif clave1 != clave2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(username=usuario).exists():
            messages.error(request, "El nombre de usuario ya está registrado.")
        else:
            user = User.objects.create_user(username=usuario, email=email, password=clave1)
            user.first_name = nombres
            user.last_name = apellidos
            user.save()
            # El UserProfile se crea automáticamente con la señal post_save
            nombre_completo = f"{nombres} {apellidos}".strip()
            user.profile.nombre_completo = nombre_completo
            user.profile.telefono = telefono
            user.profile.direccion = direccion
            user.profile.save()
            login(request, user)
            messages.success(request, f"Cuenta creada con éxito. ¡Bienvenido, {nombre_completo}!")
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
        
        if request.user.profile.role == 'admin':
            remitente_id = request.POST.get("remitente_id")
            try:
                remitente_obj = User.objects.get(id=remitente_id)
                nombre_remitente = remitente_obj.get_full_name() or remitente_obj.username
            except User.DoesNotExist:
                messages.error(request, "El cliente seleccionado no existe.")
                return redirect("crear_envio")
        else:
            remitente_obj = request.user
            nombre_remitente = remitente_obj.get_full_name() or remitente_obj.username

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
                peso_val = float(peso)
                costo_val = float(costo) if costo else 0
                if peso_val <= 0:
                    messages.error(request, "El peso del paquete debe ser mayor a 0 kg.")
                    return render(request, "crear_envio.html", _context_crear_envio(request))
                if costo_val < 0:
                    messages.error(request, "El costo del envío no puede ser negativo.")
                    return render(request, "crear_envio.html", _context_crear_envio(request))

                eta = None
                if eta_raw:
                    try:
                        eta = datetime.strptime(eta_raw, "%Y-%m-%dT%H:%M")
                        ahora = datetime.now()
                        manana = ahora + timedelta(days=1)
                        manana = manana.replace(hour=0, minute=0, second=0, microsecond=0)
                        if eta.replace(tzinfo=None) < manana:
                            messages.error(request, "La fecha estimada de llegada debe ser al menos 1 día en el futuro.")
                            return render(request, "crear_envio.html", _context_crear_envio(request))
                    except ValueError:
                        messages.error(request, "El formato de la fecha estimada no es válido.")
                        return render(request, "crear_envio.html", _context_crear_envio(request))

                envio = Envio.objects.create(
                    remitente=remitente_obj,
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
                _enviar_guia_por_correo(request, envio)
                if request.user.profile.role == 'admin':
                    return redirect("admin_envios")
                return redirect("mis_envios")
            except Exception as e:
                messages.error(request, f"Error al registrar la encomienda: {str(e)}")

    context = _context_crear_envio(request)
    return render(request, "crear_envio.html", context)


def _context_crear_envio(request):
    context = {}
    if request.user.profile.role == 'admin':
        context['usuarios_clientes'] = User.objects.filter(profile__role='cliente')
    else:
        context['nombre_remitente_display'] = request.user.profile.get_display_name()
    return context


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
        nuevo_estado = request.POST.get("estado", envio.estado)
        ubicacion_actual = request.POST.get("ubicacion_actual", "").strip()
        transporte = request.POST.get("transporte", "").strip()
        observaciones = request.POST.get("observaciones", "").strip()
        eta_raw = request.POST.get("hora_estimada_llegada", "").strip()

        if nuevo_estado not in dict(Envio.ESTADO_CHOICES):
            messages.error(request, "Estado no válido.")
            return redirect("admin_envios")

        envio.estado = nuevo_estado

        if ubicacion_actual:
            envio.ubicacion_actual = ubicacion_actual
        if transporte:
            envio.transporte = transporte
        if observaciones:
            envio.observaciones = observaciones

        if eta_raw:
            try:
                eta = datetime.strptime(eta_raw, "%Y-%m-%dT%H:%M")
                if eta.replace(tzinfo=None) < datetime.now():
                    messages.error(request, "La fecha estimada de llegada no puede ser anterior a la fecha y hora actual.")
                    return render(request, "admin_actualizar_envio.html", {"envio": envio})
                envio.hora_estimada_llegada = eta
            except ValueError:
                messages.error(request, "El formato de la fecha estimada no es válido.")
                return render(request, "admin_actualizar_envio.html", {"envio": envio})

        if nuevo_estado == 'entregado':
            envio.ubicacion_actual = f"Entregado con éxito en {envio.ciudad_destino} ({envio.direccion_destinatario})"

        envio.save()

        messages.success(request, f"Estado de encomienda {envio.numero_tracking} actualizado a '{envio.get_estado_display()}'.")
        return redirect("admin_envios")

    return render(request, "admin_actualizar_envio.html", {"envio": envio})


# ============================================================
# FUNCIONES AUXILIARES: QR EN BASE64 Y ENVÍO DE PDF POR CORREO
# ============================================================

def _generar_qr_base64(tracking_code, request=None, envio=None):
    """Genera el QR con datos del envío como cadena base64 (para incrustar en PDF)."""
    if envio:
        qr_data = (
            f"Tracking: {envio.numero_tracking}\n"
            f"Remitente: {envio.nombre_remitente}\n"
            f"Destinatario: {envio.nombre_destinatario}\n"
            f"Fecha Recepcion: {envio.fecha_recepcion.strftime('%d/%m/%Y %H:%M')}"
        )
    else:
        qr_data = tracking_code

    if request:
        tracking_url = request.build_absolute_uri(f'/rastrear/{tracking_code}/')
    else:
        tracking_url = f'http://nexoraexpress.com/rastrear/{tracking_code}/'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_bytes = buffer.getvalue()
    return base64.b64encode(qr_bytes).decode('utf-8'), tracking_url


def _generar_pdf_bytes(envio, request=None):
    """Genera el PDF de la guía de envío como bytes (para adjuntar en correo)."""
    qr_base64, tracking_url = _generar_qr_base64(envio.numero_tracking, request, envio=envio)
    template = get_template('guia_pdf.html')
    context = {
        'envio': envio,
        'qr_base64': qr_base64,
        'tracking_url': tracking_url,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    html = template.render(context)
    buffer = BytesIO()
    pisa.CreatePDF(html, dest=buffer)
    return buffer.getvalue()


def _enviar_guia_por_correo(request, envio):
    """Envía la guía PDF por correo al remitente (si tiene email) y al destinatario."""
    destinatarios = []
    
    # Correo del remitente (cliente que creó el envío)
    if envio.remitente.email:
        destinatarios.append(envio.remitente.email)
    
    # Correo del destinatario (si fue registrado)
    if envio.correo_destinatario and envio.correo_destinatario not in destinatarios:
        destinatarios.append(envio.correo_destinatario)
    
    if not destinatarios:
        return  # No hay correos, saltar silenciosamente
    
    try:
        pdf_bytes = _generar_pdf_bytes(envio, request)
        
        nombre_remitente = envio.nombre_remitente
        asunto = f'✅ Guía de Envío Registrada — NEXORA EXPRESS | {envio.numero_tracking}'
        cuerpo = (
            f'Estimado/a {nombre_remitente},\n\n'
            f'Su encomienda ha sido registrada exitosamente en NEXORA EXPRESS.\n\n'
            f'📦 Número de Tracking: {envio.numero_tracking}\n'
            f'🏙️ Origen: {envio.origen} — {envio.oficina}\n'
            f'📍 Destino: {envio.ciudad_destino}\n'
            f'👤 Destinatario: {envio.nombre_destinatario}\n'
            f'💰 Costo: ${envio.costo}\n\n'
            f'Adjunto encontrará la guía de envío en formato PDF lista para imprimir.\n\n'
            f'Puede rastrear su encomienda en:\n'
            f'http://nexoraexpress.com/rastrear/{envio.numero_tracking}/\n\n'
            f'Gracias por confiar en NEXORA EXPRESS.\n'
            f'— Equipo NEXORA EXPRESS'
        )
        
        email = EmailMessage(
            subject=asunto,
            body=cuerpo,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@nexoraexpress.com'),
            to=destinatarios,
        )
        email.attach(
            filename=f'Guia_{envio.numero_tracking}.pdf',
            content=pdf_bytes,
            mimetype='application/pdf',
        )
        email.send(fail_silently=True)
    except Exception:
        pass  # El correo nunca debe bloquear el flujo principal


@login_required
def reenviar_guia(request, envio_id):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({"success": False, "message": "Sin permisos."}, status=403)

    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Método no permitido."}, status=405)

    envio = get_object_or_404(Envio, id=envio_id)
    _enviar_guia_por_correo(request, envio)
    return JsonResponse({"success": True, "message": f"Guía reenviada exitosamente a los correos registrados del envío {envio.numero_tracking}."})


@login_required
def descargar_guia_pdf(request, tracking_code):
    envio = get_object_or_404(Envio, numero_tracking__iexact=tracking_code)
    
    is_owner = (request.user == envio.remitente)
    is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

    if not (is_owner or is_admin):
        messages.error(request, "Acceso denegado a la guía PDF.")
        return redirect("inicio")

    qr_base64, tracking_url = _generar_qr_base64(envio.numero_tracking, request, envio=envio)
    
    context = {
        'envio': envio,
        'qr_base64': qr_base64,
        'tracking_url': tracking_url,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Guia_{envio.numero_tracking}.pdf"'
    
    template = get_template('guia_pdf.html')
    html = template.render(context, request)

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error generando el PDF')
    return response


@login_required
def reporte_ingresos_pdf(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, "Acceso denegado. Solo administradores pueden generar este reporte.")
        return redirect("inicio")

    # Metrics
    now = timezone.now()
    envios = Envio.objects.filter(
        fecha_creacion__year=now.year,
        fecha_creacion__month=now.month
    ).order_by('-fecha_creacion')

    recaudado_mes = envios.aggregate(Sum('costo'))['costo__sum'] or 0

    template_path = 'reporte_ingresos_pdf.html'
    context = {
        'envios': envios,
        'recaudado_mes': recaudado_mes,
        'mes_actual': now.strftime("%B %Y"),
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Reporte_Ingresos_{now.strftime("%Y_%m")}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context, request)

    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error generando el PDF de Ingresos')
    return response
