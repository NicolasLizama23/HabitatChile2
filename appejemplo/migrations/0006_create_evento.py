from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('appejemplo', '0005_add_latlong_to_proyectos'),
    ]

    operations = [
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id_evento', models.AutoField(primary_key=True, serialize=False)),
                ('titulo', models.CharField(max_length=200)),
                ('tipo', models.CharField(blank=True, max_length=50, null=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('hora_inicio', models.TimeField(blank=True, null=True)),
                ('hora_fin', models.TimeField(blank=True, null=True)),
                ('ubicacion', models.CharField(blank=True, max_length=255, null=True)),
                ('all_day', models.BooleanField(default=False)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_creados', to='auth.user')),
                ('proyecto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='appejemplo.proyectoshabitacionales')),
            ],
            options={
                'db_table': 'eventos',
            },
        ),
        migrations.AddField(
            model_name='evento',
            name='asignados',
            field=models.ManyToManyField(blank=True, to='auth.user'),
        ),
    ]
