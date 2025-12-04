"""
Algoritmo de Matching Automático para HabitatChile

Este módulo implementa el algoritmo de matching automático entre beneficiarios y proyectos
habitacionales basado en criterios socioeconómicos y de compatibilidad.
"""

from django.db.models import Q, F, Case, When, Value, IntegerField
from django.utils import timezone
from .models import Beneficiarios, ProyectosHabitacionales, Postulaciones, Matching
import logging

logger = logging.getLogger(__name__)


class MatchingAlgorithm:
    """
    Algoritmo de matching automático que asigna beneficiarios a proyectos
    basándose en criterios de compatibilidad socioeconómica.
    """

    # Pesos para el cálculo de compatibilidad
    PESOS = {
        'puntaje_socioeconomico': 0.4,  # 40%
        'ingresos_familiares': 0.3,      # 30%
        'numero_integrantes': 0.2,       # 20%
        'ubicacion': 0.1,                # 10%
    }

    # Rangos de ingresos por tipo de vivienda (ejemplo)
    RANGOS_INGRESOS = {
        'Social': (0, 800000),
        'Media': (800001, 2000000),
        'Alta': (2000001, float('inf')),
    }

    @classmethod
    def calcular_compatibilidad(cls, beneficiario, proyecto):
        """
        Calcula el puntaje de compatibilidad entre un beneficiario y un proyecto.

        Args:
            beneficiario: Instancia de Beneficiarios
            proyecto: Instancia de ProyectosHabitacionales

        Returns:
            float: Puntaje de compatibilidad (0-100)
        """
        puntaje = 0

        # 1. Puntaje socioeconómico (40%)
        if beneficiario.puntaje_socioeconomico and proyecto.precio_unitario:
            # Beneficiarios con mayor puntaje tienen prioridad en proyectos más caros
            ratio = min(beneficiario.puntaje_socioeconomico / 100, 1.0)
            puntaje += cls.PESOS['puntaje_socioeconomico'] * ratio * 100

        # 2. Compatibilidad de ingresos (30%)
        if beneficiario.ingresos_familiares:
            rango_proyecto = cls.RANGOS_INGRESOS.get(proyecto.tipo_vivienda, (0, float('inf')))
            if rango_proyecto[0] <= beneficiario.ingresos_familiares <= rango_proyecto[1]:
                puntaje += cls.PESOS['ingresos_familiares'] * 100
            elif beneficiario.ingresos_familiares < rango_proyecto[0]:
                # Penalización por ingresos muy bajos
                puntaje += cls.PESOS['ingresos_familiares'] * 50
            else:
                # Penalización por ingresos muy altos
                puntaje += cls.PESOS['ingresos_familiares'] * 30

        # 3. Número de integrantes vs tamaño de vivienda (20%)
        if beneficiario.numero_integrantes and proyecto.superficie_vivienda:
            # Ideal: 1 integrante por 40m² aproximadamente
            superficie_ideal = beneficiario.numero_integrantes * 40
            ratio_superficie = min(proyecto.superficie_vivienda / superficie_ideal, 2.0)
            puntaje += cls.PESOS['numero_integrantes'] * (ratio_superficie / 2.0) * 100

        # 4. Ubicación (10%) - preferencia por región/municipio
        if beneficiario.id_municipio and proyecto.id_municipio:
            if beneficiario.id_municipio == proyecto.id_municipio:
                puntaje += cls.PESOS['ubicacion'] * 100
            elif beneficiario.id_municipio.id_region == proyecto.id_municipio.id_region:
                puntaje += cls.PESOS['ubicacion'] * 70

        return min(puntaje, 100)  # Máximo 100 puntos

    @classmethod
    def ejecutar_matching(cls, region_id=None, municipio_id=None, limite_proyectos=None):
        """
        Ejecuta el algoritmo de matching para una región o municipio específico.

        Args:
            region_id: ID de la región (opcional)
            municipio_id: ID del municipio (opcional)
            limite_proyectos: Número máximo de proyectos a procesar (opcional)

        Returns:
            dict: Resultados del matching
        """
        logger.info(f"Iniciando matching automático - Región: {region_id}, Municipio: {municipio_id}")

        # Filtrar beneficiarios elegibles
        beneficiarios = Beneficiarios.objects.filter(
            estado_beneficiario__in=['Activo', 'Elegible']
        ).exclude(
            # Excluir beneficiarios que ya tienen matching activo
            matching__estado='Activo'
        )

        if region_id:
            beneficiarios = beneficiarios.filter(id_municipio__id_region=region_id)
        if municipio_id:
            beneficiarios = beneficiarios.filter(id_municipio=municipio_id)

        # Filtrar proyectos disponibles
        proyectos = ProyectosHabitacionales.objects.filter(
            estado_proyecto__in=['Activo', 'Disponible'],
            numero_viviendas__gt=0  # Que tengan viviendas disponibles
        )

        if region_id:
            proyectos = proyectos.filter(id_municipio__id_region=region_id)
        if municipio_id:
            proyectos = proyectos.filter(id_municipio=municipio_id)

        if limite_proyectos:
            proyectos = proyectos[:limite_proyectos]

        resultados = {
            'procesados': 0,
            'matchings_creados': 0,
            'errores': 0,
            'detalles': []
        }

        for beneficiario in beneficiarios:
            try:
                mejores_matches = []

                for proyecto in proyectos:
                    # Verificar que no haya postulación previa rechazada
                    postulacion_previa = Postulaciones.objects.filter(
                        id_beneficiario=beneficiario,
                        id_proyecto=proyecto,
                        estado_postulacion='Rechazada'
                    ).exists()

                    if postulacion_previa:
                        continue

                    compatibilidad = cls.calcular_compatibilidad(beneficiario, proyecto)

                    if compatibilidad >= 60:  # Umbral mínimo de compatibilidad
                        mejores_matches.append({
                            'proyecto': proyecto,
                            'compatibilidad': compatibilidad
                        })

                # Ordenar por compatibilidad y tomar los mejores
                mejores_matches.sort(key=lambda x: x['compatibilidad'], reverse=True)
                mejores_matches = mejores_matches[:3]  # Máximo 3 matches por beneficiario

                for match in mejores_matches:
                    # Crear registro de matching
                    matching, created = Matching.objects.get_or_create(
                        id_beneficiario=beneficiario,
                        id_proyecto=match['proyecto'],
                        defaults={
                            'puntaje_compatibilidad': match['compatibilidad'],
                            'fecha_matching': timezone.now(),
                            'estado': 'Pendiente'
                        }
                    )

                    if created:
                        resultados['matchings_creados'] += 1
                        resultados['detalles'].append({
                            'beneficiario': f"{beneficiario.nombre} {beneficiario.apellidos}",
                            'proyecto': match['proyecto'].nombre_proyecto,
                            'compatibilidad': match['compatibilidad']
                        })

                resultados['procesados'] += 1

            except Exception as e:
                logger.error(f"Error procesando beneficiario {beneficiario.id_beneficiario}: {str(e)}")
                resultados['errores'] += 1

        logger.info(f"Matching completado - Procesados: {resultados['procesados']}, Matchings: {resultados['matchings_creados']}")
        return resultados

    @classmethod
    def aprobar_matching(cls, matching_id, usuario_aprobador=None):
        """
        Aprueba un matching y crea la postulación correspondiente.

        Args:
            matching_id: ID del matching a aprobar
            usuario_aprobador: Usuario que aprueba (opcional)

        Returns:
            bool: True si se aprobó correctamente
        """
        try:
            matching = Matching.objects.get(id_matching=matching_id, estado='Pendiente')

            # Crear postulación
            postulacion = Postulaciones.objects.create(
                id_beneficiario=matching.id_beneficiario,
                id_proyecto=matching.id_proyecto,
                fecha_postulacion=timezone.now().date(),
                estado_postulacion='Aprobada',
                fecha_aprobacion=timezone.now(),
                puntaje_asignado=matching.puntaje_compatibilidad
            )

            # Actualizar matching
            matching.estado = 'Aprobado'
            matching.fecha_aprobacion = timezone.now()
            matching.save()

            # Reducir contador de viviendas disponibles
            proyecto = matching.id_proyecto
            if proyecto.numero_viviendas and proyecto.numero_viviendas > 0:
                proyecto.numero_viviendas -= 1
                proyecto.save()

            # Log de auditoría
            from .models import LogAuditoria
            LogAuditoria.objects.create(
                id_usuario=usuario_aprobador.userprofile.usuariosistema if usuario_aprobador and hasattr(usuario_aprobador, 'userprofile') else None,
                accion='APROBAR_MATCHING',
                tabla='Matching',
                registro_afectado=matching.id_matching,
                datos_anteriores={'estado': 'Pendiente'},
                datos_nuevos={'estado': 'Aprobado', 'fecha_aprobacion': timezone.now().isoformat()}
            )

            return True

        except Exception as e:
            logger.error(f"Error aprobando matching {matching_id}: {str(e)}")
            return False

    @classmethod
    def rechazar_matching(cls, matching_id, motivo=None, usuario_rechazador=None):
        """
        Rechaza un matching.

        Args:
            matching_id: ID del matching a rechazar
            motivo: Motivo del rechazo (opcional)
            usuario_rechazador: Usuario que rechaza (opcional)

        Returns:
            bool: True si se rechazó correctamente
        """
        try:
            matching = Matching.objects.get(id_matching=matching_id, estado='Pendiente')
            matching.estado = 'Rechazado'
            matching.fecha_rechazo = timezone.now()
            matching.motivo_rechazo = motivo
            matching.save()

            # Log de auditoría
            from .models import LogAuditoria
            LogAuditoria.objects.create(
                id_usuario=usuario_rechazador.userprofile.usuariosistema if usuario_rechazador and hasattr(usuario_rechazador, 'userprofile') else None,
                accion='RECHAZAR_MATCHING',
                tabla='Matching',
                registro_afectado=matching.id_matching,
                datos_anteriores={'estado': 'Pendiente'},
                datos_nuevos={'estado': 'Rechazado', 'motivo_rechazo': motivo}
            )

            return True

        except Exception as e:
            logger.error(f"Error rechazando matching {matching_id}: {str(e)}")
            return False
