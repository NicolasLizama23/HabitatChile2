from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Regiones(models.Model):
    id_region = models.AutoField(primary_key=True)
    nombre_region = models.CharField(max_length=100)
    codigo_region = models.CharField(max_length=10, blank=True, null=True)
    capital_regional = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'regiones'

    def __str__(self):
        return self.nombre_region


class Municipios(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    nombre_municipio = models.CharField(max_length=100)
    codigo_municipio = models.CharField(max_length=10, blank=True, null=True)
    id_region = models.ForeignKey('Regiones', models.DO_NOTHING, db_column='id_region', blank=True, null=True)
    poblacion = models.IntegerField(blank=True, null=True)
    superficie_km2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'municipios'

    def __str__(self):
        return self.nombre_municipio


class Beneficiarios(models.Model):
    id_beneficiario = models.AutoField(primary_key=True)
    rut = models.CharField(unique=True, max_length=20, blank=True, null=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellidos = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    id_municipio = models.ForeignKey('Municipios', models.DO_NOTHING, db_column='id_municipio', blank=True, null=True)
    estado_civil = models.CharField(max_length=50, blank=True, null=True)
    ingresos_familiares = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    numero_integrantes = models.IntegerField(blank=True, null=True)
    puntaje_socioeconomico = models.IntegerField(blank=True, null=True)
    estado_beneficiario = models.CharField(max_length=50, blank=True, null=True)
    fecha_registro = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'beneficiarios'

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"


class EmpresasConstructoras(models.Model):
    id_empresa = models.AutoField(primary_key=True)
    rut_empresa = models.CharField(unique=True, max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    latitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True,
                                  validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)])
    longitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True,
                                   validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)])
    certificacion_industrializada = models.IntegerField(blank=True, null=True)
    años_experiencia = models.IntegerField(blank=True, null=True)
    capacidad_construccion_anual = models.IntegerField(blank=True, null=True)
    estado_empresa = models.CharField(max_length=50, blank=True, null=True)
    fecha_registro = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'empresas_constructoras'

    def __str__(self):
        return self.razon_social


class Instituciones(models.Model):
    id_institucion = models.AutoField(primary_key=True)
    nombre_institucion = models.CharField(max_length=200, blank=True, null=True)
    tipo_institucion = models.CharField(max_length=100, blank=True, null=True)
    rut_institucion = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email_contacto = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'instituciones'

    def __str__(self):
        return self.nombre_institucion


class Terrenos(models.Model):
    id_terreno = models.AutoField(primary_key=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    id_municipio = models.ForeignKey('Municipios', models.DO_NOTHING, db_column='id_municipio', blank=True, null=True)
    superficie_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    coordenadas_gps = models.CharField(max_length=50, blank=True, null=True)
    latitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True)
    longitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True)
    servicios_agua = models.IntegerField(blank=True, null=True)
    servicios_electricidad = models.IntegerField(blank=True, null=True)
    servicios_alcantarillado = models.IntegerField(blank=True, null=True)
    acceso_transporte = models.IntegerField(blank=True, null=True)
    factibilidad_construccion = models.IntegerField(blank=True, null=True)
    estado_terreno = models.CharField(max_length=50, blank=True, null=True)
    precio_m2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fecha_registro = models.DateField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'terrenos'

    def __str__(self):
        return self.direccion


class ProyectosHabitacionales(models.Model):
    id_proyecto = models.AutoField(primary_key=True)
    nombre_proyecto = models.CharField(max_length=200, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    id_municipio = models.ForeignKey('Municipios', models.DO_NOTHING, db_column='id_municipio', blank=True, null=True)
    id_empresa_constructora = models.ForeignKey(EmpresasConstructoras, models.DO_NOTHING, db_column='id_empresa_constructora', blank=True, null=True)
    id_terreno = models.ForeignKey('Terrenos', models.DO_NOTHING, db_column='id_terreno', blank=True, null=True)
    latitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True)
    longitud = models.DecimalField(max_digits=14, decimal_places=10, blank=True, null=True)
    numero_viviendas = models.IntegerField(blank=True, null=True)
    tipo_vivienda = models.CharField(max_length=100, blank=True, null=True)
    superficie_vivienda = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin_estimada = models.DateField(blank=True, null=True)
    estado_proyecto = models.CharField(max_length=50, blank=True, null=True)
    certificacion_ambiental = models.CharField(max_length=50, blank=True, null=True)
    tecnologia_construccion = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'proyectos_habitacionales'

    def __str__(self):
        return self.nombre_proyecto

    def clean(self):
        # Validar rango de coordenadas si existen
        errors = {}
        if self.latitud is not None:
            try:
                v = float(self.latitud)
                if v < -90 or v > 90:
                    errors['latitud'] = 'Latitud debe estar entre -90 y 90.'
            except (TypeError, ValueError):
                errors['latitud'] = 'Latitud inválida.'
        if self.longitud is not None:
            try:
                v = float(self.longitud)
                if v < -180 or v > 180:
                    errors['longitud'] = 'Longitud debe estar entre -180 y 180.'
            except (TypeError, ValueError):
                errors['longitud'] = 'Longitud inválida.'

        if errors:
            raise ValidationError(errors)


class Postulaciones(models.Model):
    id_postulacion = models.AutoField(primary_key=True)
    id_beneficiario = models.ForeignKey(Beneficiarios, models.DO_NOTHING, db_column='id_beneficiario', blank=True, null=True)
    id_proyecto = models.ForeignKey('ProyectosHabitacionales', models.DO_NOTHING, db_column='id_proyecto', blank=True, null=True)
    fecha_postulacion = models.DateField(blank=True, null=True)
    estado_postulacion = models.CharField(max_length=50, blank=True, null=True)
    puntaje_asignado = models.IntegerField(blank=True, null=True)
    fecha_asignacion = models.DateField(blank=True, null=True)
    fecha_aprobacion = models.DateField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    documentos_adjuntos = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'postulaciones'

    def __str__(self):
        return f"Postulación {self.id_postulacion}"


class UsuariosSistema(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    username = models.CharField(unique=True, max_length=100, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellidos = models.CharField(max_length=100, blank=True, null=True)
    tipo_usuario = models.CharField(max_length=50, blank=True, null=True)
    id_institucion = models.ForeignKey(Instituciones, models.DO_NOTHING, db_column='id_institucion', blank=True, null=True)
    estado_usuario = models.CharField(max_length=50, blank=True, null=True)
    fecha_ultimo_acceso = models.DateTimeField(blank=True, null=True)
    fecha_registro = models.DateField(blank=True, null=True)
    # Vinculación opcional a Beneficiarios para relacionar usuarios del sistema con su registro beneficiario
    beneficiario = models.OneToOneField('Beneficiarios', models.SET_NULL, db_column='id_beneficiario_rel', blank=True, null=True)
    # Si el usuario es una empresa, permite vincularla a una entrada de EmpresasConstructoras
    id_empresa = models.ForeignKey('EmpresasConstructoras', models.SET_NULL, db_column='id_empresa_rel', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'usuarios_sistema'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    """Perfil vinculado a `auth.User` para manejar el tipo de usuario en la app.

    Se crea automáticamente cuando se crea un `User`.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo_usuario = models.CharField(max_length=50, choices=(('admin','admin'),('usuario','usuario'),('empresa','empresa')), default='usuario')
    usuariosistema = models.OneToOneField(UsuariosSistema, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.tipo_usuario})"


class LogAuditoria(models.Model):
    id_log = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(UsuariosSistema, models.SET_NULL, db_column='id_usuario', blank=True, null=True)
    accion = models.CharField(max_length=100, blank=True, null=True)
    tabla = models.CharField(max_length=100, blank=True, null=True)
    registro_afectado = models.IntegerField(blank=True, null=True)
    datos_anteriores = models.JSONField(blank=True, null=True)
    datos_nuevos = models.JSONField(blank=True, null=True)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'log_auditoria'

    def __str__(self):
        return f"{self.accion} - {self.timestamp}"


class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(UsuariosSistema, models.CASCADE, db_column='id_usuario')
    tipo = models.CharField(max_length=50, blank=True, null=True)  # Email, SMS, In-App
    mensaje = models.TextField(blank=True, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    canal = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'notificacion'

    def __str__(self):
        return f"Notificación {self.tipo} - {self.id_usuario.username}"


class Matching(models.Model):
    id_matching = models.AutoField(primary_key=True)
    id_beneficiario = models.ForeignKey(Beneficiarios, models.CASCADE, db_column='id_beneficiario')
    id_proyecto = models.ForeignKey(ProyectosHabitacionales, models.CASCADE, db_column='id_proyecto')
    puntaje_compatibilidad = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    fecha_matching = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, default='Pendiente')

    class Meta:
        managed = True
        db_table = 'matching'

    def __str__(self):
        return f"Matching {self.id_beneficiario.nombre} - {self.id_proyecto.nombre_proyecto}"


class Evento(models.Model):
    """Modelo simple para eventos del calendario (citas, visitas, tareas)."""
    id_evento = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=50, blank=True, null=True)  # task, meeting, deadline, project, visit, etc.
    descripcion = models.TextField(blank=True, null=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    hora_inicio = models.TimeField(blank=True, null=True)
    hora_fin = models.TimeField(blank=True, null=True)
    proyecto = models.ForeignKey(ProyectosHabitacionales, models.SET_NULL, db_column='id_proyecto_rel', blank=True, null=True)
    asignados = models.ManyToManyField(User, blank=True)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    all_day = models.BooleanField(default=False)
    creado_por = models.ForeignKey(User, models.SET_NULL, db_column='creado_por', blank=True, null=True, related_name='eventos_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'eventos'

    def __str__(self):
        return f"{self.titulo} ({self.fecha_inicio})"
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except Exception:
        # perfil puede no existir en edge cases
        pass
