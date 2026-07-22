import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NEXORA_EXPRESS.settings')
django.setup()

from django.contrib.auth.models import User

def actualizar_nombres():
    usuarios = User.objects.all()
    actualizados = 0

    for usuario in usuarios:
        if not usuario.first_name and not usuario.last_name and usuario.email:
            # Parse email (e.g. juan.perez123@utc.edu.ec -> "Juan", "Perez")
            # Split by @
            email_parts = usuario.email.split('@')
            if len(email_parts) > 0:
                name_part = email_parts[0]
                
                # Remove digits
                name_letters = ''.join([i for i in name_part if not i.isdigit()])
                
                # Split by dot or underscore
                name_tokens = name_letters.replace('_', '.').split('.')
                
                first_name = ""
                last_name = ""
                
                if len(name_tokens) >= 2:
                    first_name = name_tokens[0].capitalize()
                    last_name = name_tokens[1].capitalize()
                elif len(name_tokens) == 1:
                    first_name = name_tokens[0].capitalize()
                
                usuario.first_name = first_name
                usuario.last_name = last_name
                usuario.save()
                print(f"Usuario {usuario.username} actualizado: {usuario.first_name} {usuario.last_name}")
                actualizados += 1
                
    print(f"Total de usuarios actualizados: {actualizados}")

if __name__ == "__main__":
    actualizar_nombres()
