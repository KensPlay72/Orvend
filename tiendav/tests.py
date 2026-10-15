import json
from uuid import UUID

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from .tokens import id_desde_token_categoria, token_categoria
from .views import crear_pedido


class TokensCategoriaTests(SimpleTestCase):
    def test_categoria_usa_token_en_url_y_se_resuelve(self):
        token = token_categoria(27)

        self.assertNotEqual(token, "27")
        self.assertEqual(id_desde_token_categoria(token), 27)

    def test_categoria_acepta_enlaces_anteriores_con_id(self):
        self.assertEqual(id_desde_token_categoria("27"), 27)

    def test_categoria_rechaza_token_modificado(self):
        token = token_categoria(27)
        modificado = ("A" if token[0] != "A" else "B") + token[1:]

        self.assertIsNone(id_desde_token_categoria(modificado))


class TiendaRutasPublicasTests(SimpleTestCase):
    def test_inicio_tienda_tiene_ruta_publica(self):
        self.assertEqual(reverse("tiendav:inicio"), "/tienda/")

    def test_detalle_producto_usa_token_publico(self):
        token = UUID("12345678-1234-5678-1234-567812345678")
        self.assertEqual(
            reverse("tiendav:detalle_producto", kwargs={"token": token}),
            f"/tienda/producto/{token}/",
        )

    def test_cuenta_y_historial_tienen_rutas_publicas(self):
        self.assertEqual(reverse("tiendav:cuenta"), "/tienda/cuenta/")
        self.assertEqual(reverse("tiendav:historial"), "/tienda/mis-pedidos/")
        self.assertEqual(reverse("tiendav:perfil"), "/tienda/mi-perfil/")

    def test_manager_tiene_rutas_de_pedidos(self):
        self.assertEqual(reverse("pedidos_tienda"), "/manager/pedidos-tienda/")
        self.assertEqual(
            reverse("procesar_pedido_tienda", kwargs={"pedido_id": 12}),
            "/manager/pedidos-tienda/12/procesar/",
        )

    def test_crear_pedido_exige_sesion_de_cliente(self):
        request = RequestFactory().post(
            reverse("tiendav:crear_pedido"),
            data="{}",
            content_type="application/json",
        )
        request.session = {}
        response = crear_pedido(request)
        self.assertEqual(response.status_code, 401)
        self.assertTrue(json.loads(response.content)["auth_required"])
