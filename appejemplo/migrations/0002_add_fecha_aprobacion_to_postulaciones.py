# Generated manually for adding fecha_aprobacion to Postulaciones

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appejemplo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='postulaciones',
            name='fecha_aprobacion',
            field=models.DateField(blank=True, null=True),
        ),
    ]
