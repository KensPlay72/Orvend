from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import Categorias, Clientes


class SearchClientesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="secret123"
        )
        self.user.user_permissions.add(Permission.objects.get(codename="view_clientes"))
        self.user.save()

        self.cliente = Clientes.objects.create(
            dni="0801199912345",
            nombre="Carlos",
            apellido="Hernández",
            empresa="Orvend",
            telefono="99999999",
        )

    def test_search_clientes_returns_matching_clients(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("search_clientes"), {"search": "Carlos"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["id"] == self.cliente.id for item in data))
        self.assertTrue(any("Carlos" in item["nombre_completo"] for item in data))


class SearchSelectorSuggestionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="selector_tester", password="secret123"
        )
        self.user.save()

    def test_search_categorias_returns_initial_suggestions_for_empty_query(self):
        self.client.force_login(self.user)
        categoria = Categorias.objects.create(
            nombre="Bebidas",
            descripcion="Categoría de prueba",
            is_active=True,
            is_delete=False,
        )

        response = self.client.get(reverse("search_categorias"), {"search": ""})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["id"] == categoria.id for item in data))
