from urllib.parse import unquote, urlsplit

from django.db import migrations, models


def guardar_nombre_remoto(apps, schema_editor):
    ProductosImagenes = apps.get_model("manager", "ProductosImagenes")

    for imagen in ProductosImagenes.objects.exclude(imagen_url__isnull=True).exclude(imagen_url=""):
        nombre = unquote(urlsplit(imagen.imagen_url).path.rsplit("/", 1)[-1])
        if nombre:
            imagen.imagen_archivo = nombre
            imagen.save(update_fields=["imagen_archivo"])


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0015_permiso_modificar_precio_caja"),
    ]

    operations = [
        migrations.AddField(
            model_name="productosimagenes",
            name="imagen_archivo",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.RunPython(guardar_nombre_remoto, migrations.RunPython.noop),
    ]
