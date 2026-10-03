"""Mediciones reproducibles para los listados críticos del ERP."""

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import CaptureQueriesContext

from manager.models import Compras, Inventarios, Productos


class Command(BaseCommand):
    help = "Mide consultas y tiempo de los listados críticos; permite comparar dos ejecuciones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--guardar",
            metavar="ARCHIVO.json",
            help="Guarda esta medición para compararla después de una migración.",
        )
        parser.add_argument(
            "--comparar",
            metavar="ARCHIVO.json",
            help="Compara el resultado actual contra una medición guardada.",
        )
        parser.add_argument(
            "--explain",
            action="store_true",
            help="Muestra el plan de PostgreSQL para los listados indexados.",
        )

    @staticmethod
    def _medir(queryset):
        inicio = time.perf_counter()
        with CaptureQueriesContext(connection) as consultas:
            list(queryset)
        return {
            "milisegundos": round((time.perf_counter() - inicio) * 1000, 2),
            "consultas": len(consultas),
        }

    def handle(self, *args, **options):
        pruebas = {
            "productos_pagina_1": Productos.objects.filter(
                is_delete=False, is_active=True
            )
            .select_related("categoria", "marca", "unidad_medida")
            .order_by("nombre")[:10],
            "compras_recepcion": Compras.objects.filter(is_delete=False)
            .select_related("proveedor", "ubicacion", "llegada_bodega_por")
            .order_by("-fecha_compra")[:10],
            "inventario_agrupado": Inventarios.objects.filter(is_delete=False)
            .values("producto_id", "ubicacion_id")
            .order_by("producto_id", "ubicacion_id")[:100],
        }
        resultados = {
            nombre: self._medir(queryset) for nombre, queryset in pruebas.items()
        }

        self.stdout.write(self.style.SUCCESS("Medición actual"))
        for nombre, dato in resultados.items():
            self.stdout.write(
                f"- {nombre}: {dato['milisegundos']} ms · {dato['consultas']} consulta(s)"
            )

        if options["explain"]:
            self.stdout.write("\nPlan de productos:")
            self.stdout.write(pruebas["productos_pagina_1"].explain())
            self.stdout.write("\nPlan de recepción:")
            self.stdout.write(pruebas["compras_recepcion"].explain())

        if options["comparar"]:
            anterior = json.loads(Path(options["comparar"]).read_text(encoding="utf-8"))
            self.stdout.write(self.style.WARNING("\nComparación"))
            for nombre, actual in resultados.items():
                previo = anterior.get(nombre)
                if not previo:
                    continue
                diferencia = round(actual["milisegundos"] - previo["milisegundos"], 2)
                signo = "+" if diferencia > 0 else ""
                self.stdout.write(
                    f"- {nombre}: {signo}{diferencia} ms; "
                    f"consultas {previo['consultas']} → {actual['consultas']}"
                )

        if options["guardar"]:
            Path(options["guardar"]).write_text(
                json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.stdout.write(self.style.SUCCESS(f"Medición guardada en {options['guardar']}"))
