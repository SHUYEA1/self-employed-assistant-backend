# Файл: backend/crm/views.py (Полная, очищенная и исправленная версия)

import datetime
from django.conf import settings
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncMonth, TruncDay, Extract
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, APIException, AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.autoken.models import Token 

from firebase_admin import auth as firebase_auth
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Client, Interaction, Transaction, GoogleCredentials, OAuthState, Tag, TimeEntry
from .serializers import (
    ClientSerializer, InteractionSerializer, TransactionSerializer,
    RegisterSerializer, TagSerializer, TimeEntrySerializer
)

User = get_user_model()

# --- Секция ViewSets ---

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user) \
               .prefetch_related('tags') \
               .annotate(total_income=Sum('transactions__amount', filter=Q(transactions__transaction_type='INC'), default=0.0),
                         total_expense=Sum('transactions__amount', filter=Q(transactions__transaction_type='EXP'), default=0.0)) \
               .order_by('-created_at') # <-- ВАЖНОЕ ИСПРАВЛЕНИЕ ДЛЯ ПАГИНАЦИИ

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.action in ['create', 'update', 'partial_update']:
            serializer.fields['tag_ids'].queryset = Tag.objects.filter(user=self.request.user)
        return serializer

class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    
    def get_queryset(self):
        queryset = Interaction.objects.filter(client__user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-interaction_date') # <-- ВАЖНОЕ ИСПРАВЛЕНИЕ ДЛЯ ПАГИНАЦИИ

    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client.user != self.request.user: 
            raise PermissionDenied("Вы не можете добавлять взаимодействия для чужих клиентов.")
        serializer.save()

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id: 
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-transaction_date') # <-- ВАЖНОЕ ИСПРАВЛЕНИЕ ДЛЯ ПАГИНАЦИИ

    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client and client.user != self.request.user: 
            raise PermissionDenied("Вы не можете добавлять транзакции для чужих клиентов.")
        serializer.save(user=self.request.user)

class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user).order_by('name') # <-- Добавил сортировку
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        queryset = TimeEntry.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-start_time') # <-- ВАЖНОЕ ИСПРАВЛЕНИЕ ДЛЯ ПАГИНАЦИИ
            
    # ... (методы perform_create, toggle_timer, get_active_timer без изменений) ...

# --- Секция APIViews ---

class GoogleLoginView(APIView):
    # ... (без изменений) ...

class FinancialSummaryView(APIView):
    # ... (без изменений) ...
    
class RegisterView(generics.CreateAPIView):
    # ... (без изменений) ...

class UpcomingBirthdaysView(APIView):
    # ... (без изменений) ...

# --- Секция Google API (Календарь, Контакты) ---

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/contacts.readonly']

def get_google_flow():
    # ... (без изменений) ...

def _get_google_service(user, service_name, version):
    # ... (без изменений) ...

class CheckGoogleAuthView(APIView):
    # ... (без изменений) ...

class GoogleCalendarInitView(APIView):
    # ... (без изменений) ...

class GoogleCalendarRedirectView(APIView):
    # ... (без изменений) ...

class GoogleContactsListView(APIView):
    # ... (без изменений) ...

class GoogleCalendarEventListView(APIView):
    # ... (без изменений) ...

class GoogleCalendarEventDetailView(APIView):
    # ... (без изменений) ...