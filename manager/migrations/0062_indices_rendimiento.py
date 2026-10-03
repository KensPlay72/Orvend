# Generated manually to keep the database changes explicit and reviewable.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0061_compras_impuestos"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="clientes",
            index=models.Index(fields=["is_delete", "id"], name="cliente_listado_idx"),
        ),
        migrations.AddIndex(
            model_name="productos",
            index=models.Index(
                fields=["is_delete", "is_active", "nombre", "id"],
                name="prod_listado_act_nombre_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="productos",
            index=models.Index(
                fields=["is_delete", "nombre", "id"], name="prod_listado_nombre_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="compras",
            index=models.Index(
                fields=["is_delete", "ubicacion", "estado", "fecha_compra"],
                name="compr_recep_ubi_est_fecha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="compras",
            index=models.Index(
                fields=["u_creo_id", "is_delete", "id"],
                name="compr_usuario_listado_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="compras",
            index=models.Index(
                fields=["is_delete", "fecha_compra"], name="compr_export_fecha_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="detallecompra",
            index=models.Index(
                fields=["compra", "producto"], name="detallecomp_compra_prod_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="detallecompra",
            index=models.Index(
                fields=["producto", "is_delete"], name="detallecomp_prod_act_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="hautorizarcompra",
            index=models.Index(
                fields=["compra", "producto"], name="hautcomp_compra_prod_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="devolucioncompra",
            index=models.Index(
                fields=["compra", "estado"], name="devcomp_compra_estado_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="devolucioncompradetalle",
            index=models.Index(
                fields=["compra", "producto"], name="devcompdet_compra_prod_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="cuentasporpagar",
            index=models.Index(
                fields=["estado", "fecha_vencimiento"], name="cxp_estado_venc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="traslados",
            index=models.Index(
                fields=["is_delete", "ubicacion_destino", "estado", "f_creacion"],
                name="traslado_dest_est_fecha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="inventarios",
            index=models.Index(
                fields=["producto", "ubicacion", "is_delete"],
                name="inv_prod_ubi_act_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="inventarios",
            index=models.Index(
                fields=["producto", "is_delete", "fvencimiento"],
                name="inv_prod_act_venc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ventas",
            index=models.Index(fields=["f_creacion"], name="venta_fecha_idx"),
        ),
        migrations.AddIndex(
            model_name="ventas",
            index=models.Index(
                fields=["sucursal", "f_creacion"], name="venta_suc_fecha_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="cuentasporcobrar",
            index=models.Index(
                fields=["estado", "fecha_vencimiento"], name="cxc_estado_venc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="detalleventa",
            index=models.Index(
                fields=["venta", "producto"], name="detalleventa_venta_prod_idx"
            ),
        ),
    ]
