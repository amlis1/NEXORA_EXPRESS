from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.files import File
from django.conf import settings
from django.utils import timezone
from io import BytesIO
import qrcode
import uuid


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='cliente')
    nombre_completo = models.CharField(max_length=200, blank=True, help_text="Nombre completo del usuario (para clientes)")
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)

    def get_display_name(self):
        """Retorna el nombre completo si existe, de lo contrario el get_full_name() o username."""
        if self.nombre_completo:
            return self.nombre_completo
        full = self.user.get_full_name()
        return full if full else self.user.username

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_cliente(self):
        return self.role == 'cliente'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Envio(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_transito', 'En Tránsito'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    numero_tracking = models.CharField(max_length=20, unique=True, editable=False)
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='envios_creados')
    
    # Origen u Oficina
    origen = models.CharField(max_length=100, default='Latacunga', help_text="Ciudad u oficina de origen")
    oficina = models.CharField(max_length=100, default='Oficina Central Latacunga', help_text="Oficina de recepción/procesamiento")
    transporte = models.CharField(max_length=100, default='Camión Exprés 01', help_text="Unidad de transporte asignada")
    
    nombre_remitente = models.CharField(max_length=100)
    telefono_remitente = models.CharField(max_length=20)
    direccion_remitente = models.TextField()

    # Destino
    ciudad_destino = models.CharField(max_length=100, default='Quito', help_text="Ciudad de destino")
    nombre_destinatario = models.CharField(max_length=100)
    telefono_destinatario = models.CharField(max_length=20)
    direccion_destinatario = models.TextField()
    correo_destinatario = models.EmailField(blank=True, help_text="Correo electrónico del destinatario")

    # Detalle encomienda
    descripcion = models.TextField(help_text="Descripción del paquete")
    peso = models.DecimalField(max_digits=8, decimal_places=2, help_text="Peso en kg")
    dimensiones = models.CharField(max_length=50, blank=True, help_text="Ej: 30x20x15 cm")

    # Estado y seguimiento
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    ubicacion_actual = models.CharField(max_length=200, default='Centro de Acopio Latacunga', help_text="Ubicación actual de la encomienda")
    hora_estimada_llegada = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora estimada de llegada (ETA)")
    observaciones = models.TextField(blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, help_text="Código QR de rastreo")

    fecha_recepcion = models.DateTimeField(default=timezone.now, help_text="Fecha y hora de recepción del paquete (se registra automáticamente)")

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_recepcion']

    def __str__(self):
        return f"{self.numero_tracking} - {self.nombre_destinatario} ({self.ciudad_destino})"

    def save(self, *args, **kwargs):
        if not self.numero_tracking:
            self.numero_tracking = f"NX-{uuid.uuid4().hex[:8].upper()}"
            
        if not self.qr_code:
            qr_data = (
                f"Tracking: {self.numero_tracking}\n"
                f"Remitente: {self.nombre_remitente}\n"
                f"Destinatario: {self.nombre_destinatario}\n"
                f"Fecha Recepcion: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
            )
            qr_img = qrcode.make(qr_data)
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            file_name = f'qr_{self.numero_tracking}.png'
            self.qr_code.save(file_name, File(buffer), save=False)
            
        super().save(*args, **kwargs)

@receiver(pre_save, sender=Envio)
def check_envio_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Envio.objects.get(pk=instance.pk)
            instance._old_estado = old_instance.estado
        except Envio.DoesNotExist:
            instance._old_estado = None
    else:
        instance._old_estado = None

@receiver(post_save, sender=Envio)
def send_envio_email(sender, instance, created, **kwargs):
    if not instance.correo_destinatario:
        return

    subject = ''
    message = ''
    
    if created:
        subject = f'📦 Encomienda Registrada — NEXORA EXPRESS | {instance.numero_tracking}'
        message = (
            f'Estimado/a {instance.nombre_destinatario},\n\n'
            f'Su encomienda ha sido registrada exitosamente en NEXORA EXPRESS.\n\n'
            f'📦 Número de Tracking: {instance.numero_tracking}\n'
            f'🏙️ Origen: {instance.origen} — {instance.oficina}\n'
            f'📍 Destino: {instance.ciudad_destino}\n'
            f'👤 Destinatario: {instance.nombre_destinatario}\n'
            f'💰 Costo: ${instance.costo}\n\n'
            f'Puede rastrear su encomienda en:\n'
            f'http://nexoraexpress.com/rastrear/{instance.numero_tracking}/\n\n'
            f'Gracias por confiar en NEXORA EXPRESS.\n'
            f'— Equipo NEXORA EXPRESS'
        )
    else:
        old_estado = getattr(instance, '_old_estado', None)
        if old_estado and old_estado != instance.estado:
            estado_texto = instance.get_estado_display()
            subject = f'🔔 Actualización de Envío — NEXORA EXPRESS | {instance.numero_tracking}'
            
            estado_emoji = {
                'pendiente': '🕒',
                'en_transito': '🚚',
                'entregado': '✅',
                'cancelado': '❌',
            }
            emoji = estado_emoji.get(instance.estado, '📦')
            
            message = (
                f'Estimado/a {instance.nombre_destinatario},\n\n'
                f'Su envío N° {instance.numero_tracking} ha sido actualizado.\n\n'
                f'📋 Detalles del envío:\n'
                f'   • Tracking: {instance.numero_tracking}\n'
                f'   • Origen: {instance.origen}\n'
                f'   • Destino: {instance.ciudad_destino}\n'
                f'   • Ubicación actual: {instance.ubicacion_actual}\n\n'
                f'{emoji} Nuevo Estado: {estado_texto}\n\n'
            )
            
            if instance.hora_estimada_llegada:
                message += f'🕐 Estimación de llegada: {instance.hora_estimada_llegada.strftime("%d/%m/%Y %H:%M")}\n\n'
            
            message += (
                f'Rastree su envío en:\n'
                f'http://nexoraexpress.com/rastrear/{instance.numero_tracking}/\n\n'
                f'Gracias por confiar en NEXORA EXPRESS.\n'
                f'— Equipo NEXORA EXPRESS'
            )

    if subject and message:
        try:
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@nexoraexpress.com'),
                to=[instance.correo_destinatario],
            )
            email.send(fail_silently=True)
        except Exception:
            pass

