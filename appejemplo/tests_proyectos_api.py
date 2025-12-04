from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from .models import EmpresasConstructoras, UsuariosSistema, ProyectosHabitacionales, UserProfile


class ProyectosAPIPermissionsTests(TestCase):
    def setUp(self):
        # Empresas
        self.company_a = EmpresasConstructoras.objects.create(razon_social='Empresa A', rut_empresa='111')
        self.company_b = EmpresasConstructoras.objects.create(razon_social='Empresa B', rut_empresa='222')

        # Usuario empresa A
        self.user_a = User.objects.create_user(username='empresa_a', password='pass')
        # userprofile is auto-created by signal
        self.user_a.userprofile.tipo_usuario = 'empresa'
        self.user_a.userprofile.save()
        self.us_a = UsuariosSistema.objects.create(username='empresa_a_sys', id_empresa=self.company_a)
        self.user_a.userprofile.usuariosistema = self.us_a
        self.user_a.userprofile.save()

        # Usuario staff
        self.staff = User.objects.create_user(username='staff', password='pass')
        self.staff.is_staff = True
        self.staff.save()

        # API clients
        self.client = APIClient()
        self.client_a = APIClient()
        self.client_staff = APIClient()
        self.client_a.force_authenticate(user=self.user_a)
        self.client_staff.force_authenticate(user=self.staff)

    def test_unauthenticated_can_list_projects(self):
        ProyectosHabitacionales.objects.create(nombre_proyecto='P1', id_empresa_constructora=self.company_a)
        r = self.client.get('/api/proyectos/')
        self.assertEqual(r.status_code, 200)

    def test_empresa_create_project_associates_to_own_company_even_if_payload_differs(self):
        payload = {'nombre_proyecto': 'Nuevo A', 'id_empresa_constructora': self.company_b.id_empresa}
        r = self.client_a.post('/api/proyectos/', payload, format='json')
        self.assertEqual(r.status_code, 201, msg=r.content)
        created = ProyectosHabitacionales.objects.get(nombre_proyecto='Nuevo A')
        self.assertIsNotNone(created.id_empresa_constructora)
        self.assertEqual(created.id_empresa_constructora.id_empresa, self.company_a.id_empresa)

    def test_staff_can_create_for_any_company(self):
        payload = {'nombre_proyecto': 'Staff P', 'id_empresa_constructora': self.company_b.id_empresa}
        r = self.client_staff.post('/api/proyectos/', payload, format='json')
        self.assertEqual(r.status_code, 201, msg=r.content)
        created = ProyectosHabitacionales.objects.get(nombre_proyecto='Staff P')
        self.assertEqual(created.id_empresa_constructora.id_empresa, self.company_b.id_empresa)
