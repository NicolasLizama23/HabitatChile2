import json
from django.contrib.auth.models import User
from appejemplo.models import EmpresasConstructoras, ProyectosHabitacionales, Evento, UsuariosSistema
from django.test import Client

# Crear usuarios de prueba
admin, created = User.objects.get_or_create(username='testadmin', defaults={'email':'admin@example.com'})
if created:
    admin.set_password('testpass')
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()

user, created = User.objects.get_or_create(username='testuser', defaults={'email':'user@example.com'})
if created:
    user.set_password('testpass')
    user.save()

company_user, created = User.objects.get_or_create(username='companyuser', defaults={'email':'company@example.com'})
if created:
    company_user.set_password('testpass')
    company_user.save()

# Crear empresa y vincular a UsuariosSistema
emp, created = EmpresasConstructoras.objects.get_or_create(rut_empresa='111', defaults={'razon_social':'EmpresaX'})
us, created = UsuariosSistema.objects.get_or_create(username='companyuser', defaults={'tipo_usuario':'empresa', 'email':'company@example.com'})
us.id_empresa = emp
us.save()

# Asegurar que el userprofile del company_user existe y apunta a UsuariosSistema
try:
    company_user.userprofile.tipo_usuario = 'empresa'
    company_user.userprofile.usuariosistema = us
    company_user.userprofile.save()
except Exception:
    pass

# Crear proyecto vinculado a la empresa
proj, created = ProyectosHabitacionales.objects.get_or_create(nombre_proyecto='ProyectoTest', defaults={'id_empresa_constructora':emp, 'estado_proyecto':'En Planificación'})

c = Client()

# Test: admin crea evento
print('--- ADMIN TEST ---')
logged = c.login(username='testadmin', password='testpass')
print('admin login', logged)
resp = c.post('/api/events/', data=json.dumps({'title':'Admin Event','start':'2025-12-01'}), content_type='application/json')
print('status', resp.status_code, 'body', resp.content)

# Test: normal user creates event and assigns to self
c.logout()
print('\n--- NORMAL USER TEST ---')
logged = c.login(username='testuser', password='testpass')
print('user login', logged)
resp = c.post('/api/events/', data=json.dumps({'title':'User Event','start':'2025-12-02','assigned_to':[user.id]}), content_type='application/json')
print('status', resp.status_code, 'body', resp.content)

# Test: company user creates event for company project
c.logout()
print('\n--- COMPANY USER TEST ---')
logged = c.login(username='companyuser', password='testpass')
print('company login', logged)
resp = c.post('/api/events/', data=json.dumps({'title':'Company Event','start':'2025-12-03','project':proj.id_proyecto}), content_type='application/json')
print('status', resp.status_code, 'body', resp.content)

print('\nDone')
