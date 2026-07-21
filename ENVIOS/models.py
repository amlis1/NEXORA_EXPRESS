from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='cliente')
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)

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

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.numero_tracking} - {self.nombre_destinatario} ({self.ciudad_destino})"

    def save(self, *args, **kwargs):
        if not self.numero_tracking:
            self.numero_tracking = f"NX-{uuid.uuid4().hex[:8].upper()}"
        if self.estado == 'entregado' and not self.ubicacion_actual.startswith('Entregado en'):
            self.ubicacion_actual = f"Entregado en destino ({self.ciudad_destino})"
        super().save(*args, **kwargs)

