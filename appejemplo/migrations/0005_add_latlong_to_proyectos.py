"""Add latitud/longitud fields to ProyectosHabitacionales.

Generated manually: adds two DecimalField nullable fields.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appejemplo', '0004_empresasconstructoras_latitud_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyectoshabitacionales',
            name='latitud',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='proyectoshabitacionales',
            name='longitud',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
