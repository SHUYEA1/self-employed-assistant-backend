from django.test import TestCase
from django.utils import timezone
from .models import Client, Interaction, Transaction, Tag, TimeEntry

from django.contrib.auth import get_user_model
User = get_user_model()

from rest_framework.test import APIClient

class InteractionSLATestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client_obj = Client.objects.create(user=self.user, name='Тестовый клиент')
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)

    def test_create_interaction_with_sla_fields(self):
        url = '/api/interactions/'
        data = {
            'client': self.client_obj.id,
            'interaction_type': 'CALL',
            'interaction_date': timezone.now(),
            'description': 'Тестовое взаимодействие',
            'due_date': (timezone.now() + timezone.timedelta(days=2)),
            'status': 'PEND',
            'completed_at': None
        }
        response = self.api_client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('due_date', response.data)
        self.assertIn('status', response.data)
        self.assertIn('completed_at', response.data)
        self.assertEqual(response.data['status'], 'PEND')

    def test_update_interaction_sla_status(self):
        interaction = Interaction.objects.create(
            client=self.client_obj,
            interaction_type='CALL',
            interaction_date=timezone.now(),
            description='SLA update',
            due_date=timezone.now() + timezone.timedelta(days=1),
            status='PEND',
        )
        url = f'/api/interactions/{interaction.id}/'
        data = {'status': 'COMP', 'completed_at': timezone.now()}
        response = self.api_client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'COMP')
        self.assertIsNotNone(response.data['completed_at'])
