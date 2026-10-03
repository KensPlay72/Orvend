from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def _ajustar_total(inventarios, producto_id, ubicacion_id, objetivo, referencia=None):
    lotes = list(
        inventarios.filter(producto_id=producto_id, ubicacion_id=ubicacion_id)
        .order_by("f_creacion", "id")
    )
    actual = sum((lote.cantidad for lote in lotes), Decimal("0"))
    diferencia = objetivo - actual

    if lotes:
        lote = lotes[-1]
        lote.cantidad += diferencia
        lote.save(update_fields=["cantidad"])
        return

    if referencia:
        inventarios.model.objects.create(
            producto_id=producto_id,
            ubicacion_id=ubicacion_id,
            compra_id=referencia.compra_id,
            cantidad=objetivo,
            stock_minimo=referencia.stock_minimo,
            fvencimiento=referencia.fvencimiento,
            u_creo_id=referencia.u_creo_id,
        )


def sincronizar_padres_e_hijos(apps, schema_editor):
    ProductosRel = apps.get_model("manager", "ProductosRel")
    Inventarios = apps.get_model("manager", "Inventarios")

    relaciones = ProductosRel.objects.filter(is_active=True, is_delete=False).select_related(
        "producto_master", "producto_relacionado"
    )
    padres = {}
    for relacion in relaciones:
        padres.setdefault(relacion.producto_master_id, []).append(relacion.producto_relacionado)

    inventarios = Inventarios.objects.filter(is_active=True, is_delete=False)
    for padre_id, hijos in padres.items():
        padre = ProductosRel.objects.filter(
            producto_master_id=padre_id, is_active=True, is_delete=False
        ).select_related("producto_master").first().producto_master
        equivalencia_padre = Decimal(padre.equival_unid or 1)

        ubicaciones = set(
            inventarios.filter(producto_id__in=[padre_id, *[h.id for h in hijos]])
            .values_list("ubicacion_id", flat=True)
        )
        for ubicacion_id in ubicaciones:
            padre_lotes = list(
                inventarios.filter(producto_id=padre_id, ubicacion_id=ubicacion_id)
                .order_by("f_creacion", "id")
            )
            total_padre = sum((lote.cantidad for lote in padre_lotes), Decimal("0"))

            equivalentes_hijos = []
            for hijo in hijos:
                total_hijo = (
                    inventarios.filter(
                        producto_id=hijo.id, ubicacion_id=ubicacion_id
                    ).aggregate(total=Sum("cantidad"))["total"]
                    or Decimal("0")
                )
                if total_hijo > 0:
                    equivalentes_hijos.append(
                        Decimal(total_hijo)
                        * Decimal(hijo.equival_unid or 1)
                        / equivalencia_padre
                    )

            objetivo_padre = min(equivalentes_hijos) if equivalentes_hijos else total_padre
            referencia = padre_lotes[-1] if padre_lotes else (
                inventarios.filter(
                    producto_id__in=[hijo.id for hijo in hijos],
                    ubicacion_id=ubicacion_id,
                ).order_by("f_creacion", "id").first()
            )
            _ajustar_total(
                inventarios, padre_id, ubicacion_id, objetivo_padre, referencia
            )

            for hijo in hijos:
                objetivo_hijo = (
                    objetivo_padre
                    * equivalencia_padre
                    / Decimal(hijo.equival_unid or 1)
                )
                _ajustar_total(
                    inventarios, hijo.id, ubicacion_id, objetivo_hijo, referencia
                )


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0046_precision_inventario_compartido"),
    ]

    operations = [
        migrations.RunPython(sincronizar_padres_e_hijos, migrations.RunPython.noop),
    ]
