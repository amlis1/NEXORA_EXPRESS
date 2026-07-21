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
    nombre_remitente = models.CharField(max_length=100)
    telefono_remitente = models.CharField(max_length=20)
    direccion_remitente = models.TextField()

    nombre_destinatario = models.CharField(max_length=100)
    telefono_destinatario = models.CharField(max_length=20)
    direccion_destinatario = models.TextField()

    descripcion = models.TextField(help_text="Descripción del paquete")
    peso = models.DecimalField(max_digits=8, decimal_places=2, help_text="Peso en kg")
    dimensiones = models.CharField(max_length=50, blank=True, help_text="Ej: 30x20x15 cm")

    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.numero_tracking} - {self.nombre_destinatario}"

    def save(self, *args, **kwargs):
        if not self.numero_tracking:
            self.numero_tracking = f"NX-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
