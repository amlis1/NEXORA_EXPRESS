from django.contrib import admin
from .models import UserProfile, Envio


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'telefono']
    list_filter = ['role']


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ['numero_tracking', 'nombre_remitente', 'nombre_destinatario', 'estado', 'fecha_creacion']
    list_filter = ['estado']
    search_fields = ['numero_tracking', 'nombre_remitente', 'nombre_destinatario']
