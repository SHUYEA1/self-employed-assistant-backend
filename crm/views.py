# Файл: backend/crm/views.py (Финальная версия с Firebase Auth)

import datetime
from django.conf import settings
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.crypto import get_random_string

from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, APIException, AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token 

# --- НОВЫЙ ИМПОРТ FIREBASE ---
from firebase_admin import auth as firebase_auth

# --- Старые импорты Google Auth нужны для Календаря/Контактов ---
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Client, Interaction, Transaction, GoogleCredentials, OAuthState, Tag
from .serializers import (
    ClientSerializer, InteractionSerializer, TransactionSerializer,
    RegisterSerializer, TagSerializer
)

User = get_user_model()


# --- VIEW ДЛЯ ВХОДА ЧЕРЕЗ GOOGLE (ПОЛНОСТЬЮ ПЕРЕПИСАН ПОД FIREBASE) ---
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        id_token = request.data.get('id_token')
        if not id_token:
            return Response({"error": "Missing Firebase ID token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Проверяем токен с помощью Firebase Admin SDK.
            # Если токен неверный, этот вызов вызовет исключение.
            decoded_token = firebase_auth.verify_id_token(id_token)
            
            email = decoded_token.get('email')
            if not email:
                return Response({"error": "Email not found in Firebase token."}, status=status.HTTP_400_BAD_REQUEST)

            # Находим или создаем нашего пользователя в Django
            user, created = User.objects.get_or_create(
                username=email,
                defaults={'email': email}
            )

            if created:
                user.set_unusable_password()
                user.save()
            
            # Создаем или получаем DRF токен для сессии
            drf_token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': drf_token.key}, status=status.HTTP_200_OK)

        except Exception as e:
            # Отлавливаем любые ошибки от Firebase (неверный токен, истекший срок и т.д.)
            raise AuthenticationFailed(f"Invalid Firebase token: {e}")

# ... (ОСТАЛЬНОЙ КОД views.py ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ) ...
class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).prefetch_related('tags').annotate(total_income=Sum('transactions__amount', filter=Q(transactions__transaction_type='INC'), default=0.0),total_expense=Sum('transactions__amount', filter=Q(transactions__transaction_type='EXP'), default=0.0))
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.action in ['create', 'update', 'partial_update']:
            serializer.fields['tag_ids'].queryset = Tag.objects.filter(user=self.request.user)
        return serializer
class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    def get_queryset(self):
        queryset = Interaction.objects.filter(client__user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:queryset = queryset.filter(client_id=client_id)
        return queryset
    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client.user != self.request.user: raise PermissionDenied("Вы не можете добавлять взаимодействия для чужих клиентов.")
        serializer.save()
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id: queryset = queryset.filter(client_id=client_id)
        return queryset
    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client and client.user != self.request.user: raise PermissionDenied("Вы не можете добавлять транзакции для чужих клиентов.")
        serializer.save(user=self.request.user)
class FinancialSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        all_time_summary = Transaction.objects.filter(user=user).annotate(month=TruncMonth('transaction_date')).values('month').annotate(income=Sum('amount', filter=Q(transaction_type='INC')), expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('month')
        this_month_summary = Transaction.objects.filter(user=user, transaction_date__year=datetime.date.today().year, transaction_date__month=datetime.date.today().month).annotate(day=TruncDay('transaction_date')).values('day').annotate(income=Sum('amount', filter=Q(transaction_type='INC')), expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('day')
        return Response({'all_time': list(all_time_summary), 'this_month': list(this_month_summary)})
class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/contacts.readonly']
def get_google_flow():
    client_config = {"web": {"client_id": settings.GOOGLE_CLIENT_ID,"client_secret": settings.GOOGLE_CLIENT_SECRET,"auth_uri": "https://accounts.google.com/o/oauth2/auth","token_uri": "https://oauth2.googleapis.com/token","auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs","redirect_uris": [settings.GOOGLE_REDIRECT_URI],}}
    return Flow.from_client_config(client_config,scopes=SCOPES,redirect_uri=settings.GOOGLE_REDIRECT_URI)
def _get_google_service(user, service_name, version):
    try:
        google_creds_model = GoogleCredentials.objects.get(user=user)
    except GoogleCredentials.DoesNotExist:
        raise APIException("Google Account is not connected.", code=status.HTTP_409_CONFLICT)
    creds = Credentials(token=google_creds_model.access_token, refresh_token=google_creds_model.refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET, scopes=SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            google_creds_model.access_token = creds.token
            google_creds_model.token_expiry = creds.expiry
            google_creds_model.save()
        except Exception as e:
            raise APIException(f"Failed to refresh Google token: {e}", code=status.HTTP_401_UNAUTHORIZED)
    return build(service_name, version, credentials=creds)
class CheckGoogleAuthView(APIView):
    def get(self, request, *args, **kwargs):
        is_authenticated = GoogleCredentials.objects.filter(user=request.user).exists()
        return Response({'isAuthenticated': is_authenticated})
class GoogleCalendarInitView(APIView):
    def get(self, request, *args, **kwargs):
        flow = get_google_flow()
        state = get_random_string(32)
        OAuthState.objects.filter(user=request.user).delete()
        OAuthState.objects.create(user=request.user, state=state)
        authorization_url, _ = flow.authorization_url(access_type='offline',prompt='consent',state=state)
        return Response({'authorization_url': authorization_url})
class GoogleCalendarRedirectView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request, *args, **kwargs):
        state_from_url = request.query_params.get('state')
        try:
            oauth_entry = OAuthState.objects.get(state=state_from_url)
            user = oauth_entry.user
            oauth_entry.delete()
        except OAuthState.DoesNotExist:
            return Response({'error': 'Invalid state parameter'}, status=status.HTTP_400_BAD_REQUEST)
        flow = get_google_flow()
        flow.state = state_from_url
        flow.fetch_token(code=request.query_params.get('code'))
        creds = flow.credentials
        GoogleCredentials.objects.update_or_create(user=user, defaults={'access_token': creds.token, 'refresh_token': creds.refresh_token, 'token_expiry': creds.expiry})
        return redirect(f"{settings.FRONTEND_URL}/calendar")
class GoogleContactsListView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            service = _get_google_service(request.user, 'people', 'v1')
            results = service.people().connections().list(resourceName='people/me', pageSize=1000, personFields='names,emailAddresses,phoneNumbers').execute()
            connections = results.get('connections', [])
            contacts_list = []
            for person in connections:
                name_item = person.get('names', [{}])[0]
                email_item = person.get('emailAddresses', [{}])[0]
                phone_item = person.get('phoneNumbers', [{}])[0]
                contacts_list.append({'name': name_item.get('displayName', 'Имя не указано'), 'email': email_item.get('value', None), 'phone': phone_item.get('value', None),})
            return Response(contacts_list)
        except HttpError as error:
            return Response({"error": f"An error occurred with Google People API: {error}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except APIException as e:
            return Response({"error": str(e)}, status=e.status_code)
class GoogleCalendarEventListView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            service = _get_google_service(request.user, 'calendar', 'v3')
            start_time_str = request.query_params.get('start')
            end_time_str = request.query_params.get('end')
            time_min = datetime.datetime.fromisoformat(start_time_str).isoformat()
            time_max = datetime.datetime.fromisoformat(end_time_str).isoformat()
            events_result = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max, maxResults=250, singleEvents=True, orderBy='startTime').execute()
            google_events = events_result.get('items', [])
            formatted_events = []
            for event in google_events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                formatted_events.append({'id': event['id'], 'title': event.get('summary', 'Без названия'), 'start': start, 'end': end,})
            return Response(formatted_events)
        except HttpError as error:
            return Response({"error": f"An error occurred with Google Calendar API: {error}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    def post(self, request, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        event_data = {'summary': request.data.get('title'), 'description': request.data.get('description'), 'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'}, 'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},}
        try:
            created_event = service.events().insert(calendarId='primary', body=event_data).execute()
            return Response(created_event, status=status.HTTP_201_CREATED)
        except HttpError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
class GoogleCalendarEventDetailView(APIView):
    def put(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        try:
            event_body = {'summary': request.data.get('title'), 'description': request.data.get('description'), 'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'}, 'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},}
            updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event_body).execute()
            return Response(updated_event)
        except HttpError as error:
            return Response({'error': str(error)}, status=error.resp.status)
    def delete(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        try:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except HttpError as error:
            return Response({'error': str(error)}, status=error.resp.status)