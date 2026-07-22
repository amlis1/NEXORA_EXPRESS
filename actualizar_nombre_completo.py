"""
Script para poblar el campo nombre_completo en UserProfile
para todos los clientes existentes que no lo tengan.

Para cliente1 (lisbeth.taco4547@utc.edu.ec):
  nombre → Lisbeth
  apellido → Taco
  nombre_completo → Lisbeth Taco
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NEXORA_EXPRESS.settings')
django.setup()

from django.contrib.auth.models import User


def extraer_nombre_de_email(email):
    """
    Extrae nombre y apellido del email.
    Ejemplo: lisbeth.taco4547@utc.edu.ec → ('Lisbeth', 'Taco')
             juan.perez123@utc.edu.ec   → ('Juan', 'Perez')
    """
    partes = email.split('@')
    if not partes:
        return '', ''
    
    nombre_parte = partes[0]
    
    # Quitar dígitos al final o en medio
    solo_letras = ''.join([c for c in nombre_parte if not c.isdigit()])
    
    # Separar por punto o guion bajo
    tokens = solo_letras.replace('_', '.').split('.')
    tokens = [t for t in tokens if t]  # eliminar vacíos
    
    nombre = tokens[0].capitalize() if len(tokens) >= 1 else ''
    apellido = tokens[1].capitalize() if len(tokens) >= 2 else ''
    
    return nombre, apellido


def actualizar_nombre_completo():
    usuarios = User.objects.filter(profile__role='cliente')
    actualizados = 0

    for usuario in usuarios:
        perfil = usuario.profile

        # Si ya tiene nombre_completo, saltar
        if perfil.nombre_completo:
            print(f"[SKIP] {usuario.username} ya tiene nombre_completo: '{perfil.nombre_completo}'")
            continue

        # Intentar desde first_name / last_name del User
        nombre_completo = ''
        if usuario.first_name or usuario.last_name:
            nombre_completo = f"{usuario.first_name} {usuario.last_name}".strip()
        elif usuario.email:
            # Extraer del email
            nombre, apellido = extraer_nombre_de_email(usuario.email)
            nombre_completo = f"{nombre} {apellido}".strip()
            # También actualizar first_name / last_name del User de Django
            if nombre:
                usuario.first_name = nombre
            if apellido:
                usuario.last_name = apellido
            usuario.save()
            print(f"  → first_name='{nombre}', last_name='{apellido}' guardados en User")
        
        if nombre_completo:
            perfil.nombre_completo = nombre_completo
            perfil.save()
            print(f"[OK] {usuario.username} → nombre_completo='{nombre_completo}'")
            actualizados += 1
        else:
            print(f"[WARN] {usuario.username} no tiene email ni nombres; se salta.")

    print(f"\nTotal de clientes actualizados: {actualizados}")


if __name__ == '__main__':
    actualizar_nombre_completo()
