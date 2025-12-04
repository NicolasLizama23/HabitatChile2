from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from appejemplo.models import UserProfile, UsuariosSistema

class Command(BaseCommand):
    help = 'Create UserProfile for users missing it and set tipo_usuario=usuario by default. Also create UsuariosSistema if missing.'

    def handle(self, *args, **options):
        users = User.objects.all()
        created_profiles = 0
        created_us = 0
        for u in users:
            profile = getattr(u, 'userprofile', None)
            if profile is None:
                profile = UserProfile.objects.create(user=u, tipo_usuario='usuario')
                created_profiles += 1
                self.stdout.write(self.style.SUCCESS(f'Created UserProfile for {u.username}'))
            else:
                if not profile.tipo_usuario:
                    profile.tipo_usuario = 'usuario'
                    profile.save()
                    self.stdout.write(self.style.SUCCESS(f'Set tipo_usuario=usuario for {u.username}'))

            # asegurar existencia de UsuariosSistema
            if not profile.usuariosistema:
                us = UsuariosSistema.objects.create(username=u.username, email=u.email, nombre=u.first_name, apellidos=u.last_name, tipo_usuario=profile.tipo_usuario)
                profile.usuariosistema = us
                profile.save()
                created_us += 1
                self.stdout.write(self.style.SUCCESS(f'Created UsuariosSistema for {u.username}'))

        self.stdout.write(self.style.SUCCESS(f'Done. profiles_created={created_profiles} usuariosistema_created={created_us}'))
