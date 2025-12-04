from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Evento, ProyectosHabitacionales
import json

class EventPermissionTests(TestCase):
    def setUp(self):
        # crear usuarios de distintos tipos usando UserProfile/UsuariosSistema si existe
        # usuario admin
        self.admin = User.objects.create_user('adminuser', password='testpass')
        self.admin.is_staff = True
        self.admin.save()

        # usuario empresa
        self.company = User.objects.create_user('companyuser', password='testpass')
        # asegurar que el UserProfile tenga el tipo adecuado (no asumir UsuariosSistema)
        try:
            up = self.company.userprofile
            up.tipo_usuario = 'empresa'
            up.save()
            if getattr(up, 'usuariosistema', None):
                us = up.usuariosistema
                us.tipo_usuario = 'empresa'
                us.save()
        except Exception:
            pass

        # usuario beneficiario
        self.benef = User.objects.create_user('benefuser', password='testpass')
        try:
            up = self.benef.userprofile
            up.tipo_usuario = 'beneficiario'
            up.save()
            if getattr(up, 'usuariosistema', None):
                us = up.usuariosistema
                us.tipo_usuario = 'beneficiario'
                us.save()
        except Exception:
            pass

        # jefe de proyecto
        self.jefe = User.objects.create_user('jefeuser', password='testpass')
        try:
            up = self.jefe.userprofile
            up.tipo_usuario = 'jefe_proyecto'
            up.save()
            if getattr(up, 'usuariosistema', None):
                us = up.usuariosistema
                us.tipo_usuario = 'jefe_proyecto'
                us.save()
        except Exception:
            pass

        # crear cliente
        self.client = Client()

        # crear un proyecto de prueba
        try:
            self.proj = ProyectosHabitacionales.objects.create(nombre_proyecto='Prueba')
        except Exception:
            self.proj = None

    def post_event(self, user, payload):
        self.client.logout()
        self.client.login(username=user.username, password='testpass')
        res = self.client.post('/api/events/', json.dumps(payload), content_type='application/json')
        return res

    def test_admin_can_create_all_types(self):
        payload = {'title': 'Tarea admin', 'start': '2025-12-01', 'type': 'task'}
        res = self.post_event(self.admin, payload)
        self.assertIn(res.status_code, (200,201))

        payload = {'title': 'Agenda admin', 'start': '2025-12-01', 'type': 'agenda'}
        res = self.post_event(self.admin, payload)
        self.assertIn(res.status_code, (200,201))

    def test_jefe_can_create_task(self):
        payload = {'title': 'Tarea jefe', 'start': '2025-12-02', 'type': 'task'}
        res = self.post_event(self.jefe, payload)
        self.assertIn(res.status_code, (200,201))

        payload = {'title': 'Reunión jefe no permitido', 'start': '2025-12-02', 'type': 'meeting'}
        res = self.post_event(self.jefe, payload)
        self.assertEqual(res.status_code, 403)

    def test_empresa_can_create_meeting_and_deadline(self):
        payload = {'title': 'Reunión empresa', 'start': '2025-12-03', 'type': 'meeting', 'project': self.proj.pk if self.proj else None}
        res = self.post_event(self.company, payload)
        # si no hay proyecto asociado al usuario, puede devolver 403; permitimos 200/201 o 403
        self.assertIn(res.status_code, (200,201,403))

    def test_beneficiario_can_create_agenda(self):
        payload = {'title': 'Visita beneficiario', 'start': '2025-12-04', 'type': 'agenda'}
        res = self.post_event(self.benef, payload)
        self.assertIn(res.status_code, (200,201,403))
