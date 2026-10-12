import uuid

from django.db import migrations, models


def asignar_tokens_merma(apps, schema_editor):
    Merma = apps.get_model("manager", "Merma")
    alias = schema_editor.connection.alias
    mermas = Merma.objects.using(alias).only("pk").iterator()
    for merma in mermas:
        Merma.objects.using(alias).filter(pk=merma.pk).update(
            documento_token=uuid.uuid4()
        )


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0066_merma"),
    ]

    operations = [
        migrations.AddField(
            model_name="merma",
            name="documento_token",
            field=models.UUIDField(
                editable=False,
                null=True,
            ),
        ),
        migrations.RunPython(
            asignar_tokens_merma,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="merma",
            name="documento_token",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
