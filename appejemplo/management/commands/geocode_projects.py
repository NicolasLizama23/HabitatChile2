from django.core.management.base import BaseCommand
from django.db.models import Q
from appejemplo.models import ProyectosHabitacionales
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time


class Command(BaseCommand):
    help = 'Geocode ProyectosHabitacionales missing lat/long using Nominatim (batch)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Max number to process (0 = all)')
        parser.add_argument('--sleep', type=float, default=1.0, help='Seconds to sleep between requests')
        parser.add_argument('--force', action='store_true', help='Overwrite existing coordinates')
        parser.add_argument('--dry-run', action='store_true', help="Don't save changes")
        parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        parser.add_argument('--municipios', type=str, default='', help='Comma-separated list of municipio names to limit processing (case-insensitive, partial match)')

    def handle(self, *args, **options):
        limit = options.get('limit') or 0
        sleep = options.get('sleep') or 1.0
        force = options.get('force')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')

        geolocator = Nominatim(user_agent='pjrEjemplo-geocode-cmd')

        qs = ProyectosHabitacionales.objects.select_related('id_terreno', 'id_municipio')
        if not force:
            qs = qs.filter(Q(latitud__isnull=True) | Q(longitud__isnull=True))

        # Filtrar por municipios si se indicó
        municipios_arg = options.get('municipios') or ''
        if municipios_arg:
            names = [n.strip() for n in municipios_arg.split(',') if n.strip()]
            if names:
                qmun = Q()
                for n in names:
                    qmun |= Q(id_municipio__nombre_municipio__icontains=n)
                qs = qs.filter(qmun)

        total = qs.count()
        self.stdout.write(self.style.NOTICE(f'Found {total} projects to process'))

        if limit and limit > 0:
            qs = qs[:limit]

        processed = 0
        updated = 0

        for p in qs:
            processed += 1
            # Build a sensible query: prefer terreno.direccion, else proyecto+municipio
            if p.id_terreno and getattr(p.id_terreno, 'direccion', None):
                municipio = p.id_municipio.nombre_municipio if p.id_municipio else ''
                qstr = f"{p.id_terreno.direccion}, {municipio}, Chile"
            else:
                municipio = p.id_municipio.nombre_municipio if p.id_municipio else ''
                qstr = f"{p.nombre_proyecto}, {municipio}, Chile"

            if verbose:
                self.stdout.write(f'[{processed}] Geocoding {p.id_proyecto}: {qstr}')

            try:
                loc = geolocator.geocode(qstr, timeout=10)
                if loc:
                    lat = round(loc.latitude, 6)
                    lon = round(loc.longitude, 6)
                    if dry_run:
                        self.stdout.write(self.style.SUCCESS(f"[DRY] {p.id_proyecto} => {lat},{lon}"))
                    else:
                        p.latitud = lat
                        p.longitud = lon
                        try:
                            p.full_clean()
                            p.save()
                            updated += 1
                            self.stdout.write(self.style.SUCCESS(f"Updated {p.id_proyecto} => {lat},{lon}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Validation/save error for {p.id_proyecto}: {e}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No geocode result for {p.id_proyecto} ({qstr})"))

            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                self.stdout.write(self.style.ERROR(f"Geocoding error for {p.id_proyecto}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Unexpected error for {p.id_proyecto}: {e}"))

            time.sleep(sleep)

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} projects, updated {updated}"))
