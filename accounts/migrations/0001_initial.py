from django.db import migrations, models


def crear_configuracion_inicial(apps, schema_editor):
    permision = apps.get_model("accounts", "permision")
    if not permision.objects.exists():
        permision.objects.create(
            login_manager=False,
            home_page=True,
            ecommerce=True,
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="permision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("login_manager", models.BooleanField(default=False)),
                ("home_page", models.BooleanField(default=False)),
                ("ecommerce", models.BooleanField(default=False)),
            ],
            options={
                "db_table": "accounts_permision",
            },
        ),
        migrations.RunPython(
            crear_configuracion_inicial,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
