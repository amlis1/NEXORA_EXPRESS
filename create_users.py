import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NEXORA_EXPRESS.settings')
django.setup()

from django.contrib.auth.models import User
from ENVIOS.models import UserProfile

def create_user(username, email, password, role):
    try:
        user = User.objects.get(username=username)
        print(f"Usuario {username} ya existe.")
    except User.DoesNotExist:
        if role == 'admin':
            user = User.objects.create_superuser(username=username, email=email, password=password)
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
        print(f"Usuario {username} creado exitosamente.")
        
    # The profile might be created by the post_save signal in models.py
    # Let's update the role explicitly.
    profile = UserProfile.objects.get(user=user)
    profile.role = role
    profile.save()
    print(f"Rol {role} asignado a {username}.")

if __name__ == '__main__':
    create_user('admin', 'esteban.ochoa8693@utc.edu.ec', 'admin123!', 'admin')
    create_user('cliente1', 'lisbeth.taco4547@utc.edu.ec', 'contraseña123!', 'cliente')
