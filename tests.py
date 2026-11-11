from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Product, Box, Order, OrderItem
from .services import recommend_box_for_order, recommend_box_for_products


class ProductModelTests(TestCase):
    def test_volume_calculation(self):
        p = Product.objects.create(
            name="Widget", length_cm=10, width_cm=5, height_cm=2, weight_kg=0.5
        )
        self.assertEqual(p.volume_cm3, Decimal('100.00'))

    def test_sorted_dimensions(self):
        p = Product.objects.create(
            name="Widget", length_cm=5, width_cm=10, height_cm=2, weight_kg=0.5
        )
        self.assertEqual(p.sorted_dimensions(), [10.0, 5.0, 2.0])


class BoxModelTests(TestCase):
    def test_volume_calculation(self):
        b = Box.objects.create(
            name="Small", length_cm=20, width_cm=15, height_cm=10,
            max_weight_kg=5, cost=1.50
        )
        self.assertEqual(b.volume_cm3, Decimal('3000.00'))


class RecommendationServiceTests(TestCase):
    def setUp(self):
        self.small_product = Product.objects.create(
            name="USB Cable", length_cm=15, width_cm=10, height_cm=3, weight_kg=0.2
        )
        self.medium_product = Product.objects.create(
            name="Monitor Stand", length_cm=35, width_cm=25, height_cm=8, weight_kg=1.5
        )
        self.heavy_product = Product.objects.create(
            name="Dumbbell", length_cm=20, width_cm=10, height_cm=10, weight_kg=12
        )

        self.tiny_box = Box.objects.create(
            name="Tiny", length_cm=12, width_cm=10, height_cm=5,
            max_weight_kg=1, cost=0.80
        )
        self.small_box = Box.objects.create(
            name="Small", length_cm=30, width_cm=20, height_cm=10,
            max_weight_kg=3, cost=1.50
        )
        self.medium_box = Box.objects.create(
            name="Medium", length_cm=40, width_cm=30, height_cm=20,
            max_weight_kg=10, cost=3.00
        )
        self.large_box = Box.objects.create(
            name="Large", length_cm=60, width_cm=40, height_cm=30,
            max_weight_kg=25, cost=6.00
        )

    def _make_order(self, order_number, items):
        order = Order.objects.create(order_number=order_number)
        for product, qty in items:
            OrderItem.objects.create(order=order, product=product, quantity=qty)
        return order

    def test_single_small_product_gets_cheapest_fitting_box(self):
        order = self._make_order("ORD-001", [(self.small_product, 1)])
        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertEqual(box.name, "Small")

    def test_weight_limit_rejects_box(self):
        order = self._make_order("ORD-002", [(self.heavy_product, 1)])
        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertEqual(box.name, "Large")

    def test_no_box_fits_returns_none(self):
        monster = Product.objects.create(
            name="Anvil", length_cm=50, width_cm=40, height_cm=30, weight_kg=100
        )
        order = self._make_order("ORD-003", [(monster, 1)])
        box = recommend_box_for_order(order)
        self.assertIsNone(box)

    def test_prefers_cheapest_among_valid(self):
        order = self._make_order("ORD-004", [(self.medium_product, 1)])
        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertEqual(box.name, "Medium")

    def test_multiple_items_volume_check(self):
        order = self._make_order("ORD-005", [(self.medium_product, 3)])
        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertIn(box.name, ["Medium", "Large"])

    def test_inactive_box_ignored(self):
        self.small_box.is_active = False
        self.small_box.save()
        order = self._make_order("ORD-006", [(self.small_product, 1)])
        box = recommend_box_for_order(order)
        self.assertEqual(box.name, "Medium")

    def test_empty_order_returns_none(self):
        order = Order.objects.create(order_number="ORD-EMPTY")
        box = recommend_box_for_order(order)
        self.assertIsNone(box)

    def test_recommend_box_for_products_helper(self):
        box = recommend_box_for_products([(self.small_product, 1)])
        self.assertIsNotNone(box)
        self.assertEqual(box.name, "Small")


class OrderAPITests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Mug", length_cm=12, width_cm=10, height_cm=12, weight_kg=0.4
        )
        self.box = Box.objects.create(
            name="Gift Box", length_cm=20, width_cm=15, height_cm=15,
            max_weight_kg=2, cost=2.00
        )

    def test_create_order_auto_recommends(self):
        payload = {
            "order_number": "API-001",
            "items": [{"product_id": self.product.id, "quantity": 1}],
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'recommended')
        self.assertEqual(response.data['recommended_box'], self.box.id)

    def test_ad_hoc_recommend(self):
        payload = {
            "products": [{"product_id": self.product.id, "quantity": 1}]
        }
        response = self.client.post('/api/recommend/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recommended_box']['name'], "Gift Box")

    def test_list_products(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)