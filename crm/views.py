import datetime
from django.conf import settings
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, APIException
from rest_framework.permissions import AllowAny, IsAuthenticated

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import Client, Interaction, Transaction, GoogleCredentials, OAuthState
from .serializers import (
    ClientSerializer, InteractionSerializer, TransactionSerializer,
    RegisterSerializer
)

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).annotate(total_income=Sum('transactions__amount', filter=Q(transactions__transaction_type='INC'), default=0.0),total_expense=Sum('transactions__amount', filter=Q(transactions__transaction_type='EXP'), default=0.0))
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


# --- ИЗМЕНЕНИЕ: Запрашиваем полный доступ, а не только чтение ---
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_flow():
    client_config = {"web": {"client_id": settings.GOOGLE_CLIENT_ID,"client_secret": settings.GOOGLE_CLIENT_SECRET,"auth_uri": "https://accounts.google.com/o/oauth2/auth","token_uri": "https://oauth2.googleapis.com/token","auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs","redirect_uris": [settings.GOOGLE_REDIRECT_URI],}}
    return Flow.from_client_config(client_config,scopes=SCOPES,redirect_uri=settings.GOOGLE_REDIRECT_URI)

# --- НОВАЯ ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ---
def _get_calendar_service(user):
    try:
        google_creds_model = GoogleCredentials.objects.get(user=user)
    except GoogleCredentials.DoesNotExist:
        raise APIException("Google Calendar is not connected.", code=status.HTTP_409_CONFLICT)

    creds = Credentials(
        token=google_creds_model.access_token,
        refresh_token=google_creds_model.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            google_creds_model.access_token = creds.token
            google_creds_model.token_expiry = creds.expiry
            google_creds_model.save()
        except Exception as e:
            raise APIException(f"Failed to refresh Google token: {e}", code=status.HTTP_401_UNAUTHORIZED)

    return build('calendar', 'v3', credentials=creds)


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


# --- VIEW ДЛЯ СПИСКА СОБЫТИЙ И СОЗДАНИЯ НОВЫХ ---
class GoogleCalendarEventListView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            service = _get_calendar_service(request.user)
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
        service = _get_calendar_service(request.user)
        event_data = {
            'summary': request.data.get('title'),
            'description': request.data.get('description'),
            'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'},
            'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},
        }
        try:
            created_event = service.events().insert(calendarId='primary', body=event_data).execute()
            return Response(created_event, status=status.HTTP_201_CREATED)
        except HttpError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

# --- НОВЫЙ VIEW ДЛЯ РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ КОНКРЕТНОГО СОБЫТИЯ ---
class GoogleCalendarEventDetailView(APIView):
    def put(self, request, event_id, *args, **kwargs):
        service = _get_calendar_service(request.user)
        try:
            event_body = {
                'summary': request.data.get('title'),
                'description': request.data.get('description'),
                'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'},
                'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},
            }
            updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event_body).execute()
            return Response(updated_event)
        except HttpError as error:
            return Response({'error': str(error)}, status=error.resp.status)

    def delete(self, request, event_id, *args, **kwargs):
        service = _get_calendar_service(request.user)
        try:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except HttpError as error:
            return Response({'error': str(error)}, status=error.resp.status)