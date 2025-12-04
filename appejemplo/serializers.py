from rest_framework import serializers
from .models import *

class RegionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regiones
        fields = '__all__'


class MunicipiosSerializer(serializers.ModelSerializer):
    nombre_region = serializers.CharField(source='id_region.nombre_region', read_only=True)
    
    class Meta:
        model = Municipios
        fields = '__all__'


class BeneficiariosSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()
    nombre_municipio = serializers.CharField(source='id_municipio.nombre_municipio', read_only=True)
    
    class Meta:
        model = Beneficiarios
        fields = '__all__'


class EmpresasConstructorasSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresasConstructoras
        fields = '__all__'


class TerrenosSerializer(serializers.ModelSerializer):
    nombre_municipio = serializers.CharField(source='id_municipio.nombre_municipio', read_only=True)
    
    class Meta:
        model = Terrenos
        fields = '__all__'


class ProyectosHabitacionalesSerializer(serializers.ModelSerializer):
    nombre_municipio = serializers.CharField(source='id_municipio.nombre_municipio', read_only=True)
    razon_social_empresa = serializers.CharField(source='id_empresa_constructora.razon_social', read_only=True)
    direccion_terreno = serializers.CharField(source='id_terreno.direccion', read_only=True)
    terreno_latitud = serializers.DecimalField(source='id_terreno.latitud', max_digits=9, decimal_places=6, read_only=True)
    terreno_longitud = serializers.DecimalField(source='id_terreno.longitud', max_digits=9, decimal_places=6, read_only=True)
    empresa_latitud = serializers.DecimalField(source='id_empresa_constructora.latitud', max_digits=9, decimal_places=6, read_only=True)
    empresa_longitud = serializers.DecimalField(source='id_empresa_constructora.longitud', max_digits=9, decimal_places=6, read_only=True)
    
    class Meta:
        model = ProyectosHabitacionales
        fields = '__all__'

    def create(self, validated_data):
        # Si el request proviene de un usuario empresa, forzamos la asociación
        # del proyecto a la empresa del usuario (si está disponible en el contexto).
        request = self.context.get('request') if hasattr(self, 'context') else None
        try:
            if request and getattr(request.user, 'is_authenticated', False):
                up = getattr(request.user, 'userprofile', None)
                if getattr(up, 'tipo_usuario', None) == 'empresa':
                    us = getattr(up, 'usuariosistema', None)
                    if us and us.id_empresa:
                        validated_data['id_empresa_constructora'] = us.id_empresa
        except Exception:
            pass
        return super().create(validated_data)


class PostulacionesSerializer(serializers.ModelSerializer):
    nombre_beneficiario = serializers.CharField(source='id_beneficiario.nombre_completo', read_only=True)
    nombre_proyecto = serializers.CharField(source='id_proyecto.nombre_proyecto', read_only=True)
    
    class Meta:
        model = Postulaciones
        fields = '__all__'
        extra_kwargs = {
            # permitir actualización parcial a través de la API
            'estado_postulacion': {'required': False},
            'fecha_asignacion': {'required': False, 'allow_null': True},
        }

    def validate_estado_postulacion(self, value):
        # Opcional: restringir a los estados conocidos
        allowed = ['Pendiente', 'En Revisión', 'Aprobada', 'Rechazada']
        if value not in allowed:
            raise serializers.ValidationError(f"Estado inválido: {value}")
        return value


class InstitucionesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instituciones
        fields = '__all__'


class UsuariosSistemaSerializer(serializers.ModelSerializer):
    nombre_institucion = serializers.CharField(source='id_institucion.nombre_institucion', read_only=True)

    class Meta:
        model = UsuariosSistema
        fields = '__all__'
        extra_kwargs = {'password_hash': {'write_only': True}}


class LogAuditoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogAuditoria
        fields = '__all__'


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'


class MatchingSerializer(serializers.ModelSerializer):
    nombre_beneficiario = serializers.CharField(source='id_beneficiario.nombre_completo', read_only=True)
    nombre_proyecto = serializers.CharField(source='id_proyecto.nombre_proyecto', read_only=True)

    class Meta:
        model = Matching
        fields = '__all__'
