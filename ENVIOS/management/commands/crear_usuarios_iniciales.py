from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ENVIOS.models import UserProfile


class Command(BaseCommand):
    help = 'Crea los usuarios iniciales del sistema (admin y cliente)'

    def handle(self, *args, **options):
        usuarios = [
            {
                'username': 'admin',
                'email': 'admin@nexora.com',
                'password': 'Admin123!',
                'role': 'admin',
                'telefono': '0991234567',
                'direccion': 'Av. Principal',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'cliente1',
                'email': 'cliente@nexora.com',
                'password': 'Cliente123!',
                'role': 'cliente',
                'telefono': '0997654321',
                'direccion': 'Calle Secundaria',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        for data in usuarios:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'is_staff': data['is_staff'],
                    'is_superuser': data['is_superuser'],
                },
            )

            user.set_password(data['password'])
            user.is_staff = data['is_staff']
            user.is_superuser = data['is_superuser']
            user.email = data['email']
            user.save()

            if created:
                msg = f"Usuario '{data['username']}' creado"
            else:
                msg = f"Usuario '{data['username']}' actualizado"

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = data['role']
            profile.telefono = data['telefono']
            profile.direccion = data['direccion']
            profile.save()

            self.stdout.write(self.style.SUCCESS(
                f"{msg} con rol '{data['role']}'"
            ))

        self.stdout.write(self.style.SUCCESS("Proceso completado."))
