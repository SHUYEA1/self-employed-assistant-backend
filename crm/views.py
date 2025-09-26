# Файл: backend/crm/views.py (С отключенной функцией PDF)

import datetime
from django.conf import settings
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncMonth, TruncDay, Extract
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import get_random_string

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, APIException, AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token 

from firebase_admin import auth as firebase_auth
import os
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

import logging
logger = logging.getLogger(__name__)


# --- ViewSets (без изменений) ---

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    
    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).prefetch_related('tags').annotate(
            total_income=Sum('transactions__amount', filter=Q(transactions__transaction_type='INC'), default=0.0),
            total_expense=Sum('transactions__amount', filter=Q(transactions__transaction_type='EXP'), default=0.0)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if self.action in ['create', 'update', 'partial_update']:
            serializer.fields['tag_ids'].queryset = Tag.objects.filter(user=self.request.user)
        return serializer

# ... InteractionViewSet, TransactionViewSet, TagViewSet, TimeEntryViewSet без изменений ...
class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    def get_queryset(self):
        queryset = Interaction.objects.filter(client__user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-interaction_date')
    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client.user != self.request.user: raise PermissionDenied("...")
        serializer.save()

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id: queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-transaction_date')
    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client and client.user != self.request.user: raise PermissionDenied("...")
        serializer.save(user=self.request.user)

class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user).order_by('name')
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TimeEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TimeEntrySerializer
    def get_queryset(self):
        queryset = TimeEntry.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by('-start_time')
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    @action(detail=False, methods=['post'], url_path='toggle-timer')
    def toggle_timer(self, request, *args, **kwargs):
        client_id = request.data.get('client_id')
        if not client_id: return Response({'error': 'client_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try: client = Client.objects.get(id=client_id, user=request.user)
        except Client.DoesNotExist: return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)
        active_timer = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        if active_timer:
            active_timer.end_time = timezone.now(); active_timer.save()
            serializer = self.get_serializer(active_timer)
            return Response({'status': 'stopped', 'entry': serializer.data})
        else:
            new_timer = TimeEntry.objects.create(user=request.user, client=client, start_time=timezone.now())
            serializer = self.get_serializer(new_timer)
            return Response({'status': 'started', 'entry': serializer.data}, status=status.HTTP_201_CREATED)
    @action(detail=False, methods=['get'], url_path='active-timer')
    def get_active_timer(self, request, *args, **kwargs):
        active_timer = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        return Response(self.get_serializer(active_timer).data if active_timer else None)

# --- APIViews ---

# Invoice generation removed

# ... GoogleLoginView, FinancialSummaryView, etc. без изменений ...
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        id_token = request.data.get('id_token')
        if not id_token: return Response({"error": "Missing Firebase ID token"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded_token = firebase_auth.verify_id_token(id_token)
            email = decoded_token.get('email')
            if not email: return Response({"error": "Email not found in Firebase token."}, status=status.HTTP_400_BAD_REQUEST)
            user, created = User.objects.get_or_create(username=email, defaults={'email': email})
            if created:
                user.set_unusable_password()
                user.save()
                logger.info(f"Created new user via GoogleLogin: {user.username}")
            else:
                logger.info(f"Existing user logged in via Google: {user.username}")

            drf_token, _ = Token.objects.get_or_create(user=user)
            # Return token plus minimal user info to make frontend integration simpler
            return Response({
                'token': drf_token.key,
                'user': {
                    'id': user.pk,
                    'username': user.username,
                    'email': getattr(user, 'email', None),
                    'created': created,
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Log full exception for easier debugging in production logs
            logger.exception("GoogleLogin failed during token verification or user creation")
            # Fallback: if a GLOBAL_API_TOKEN is configured and the request provided
            # that token in Authorization header, allow creating/returning a DRF token
            # for the email passed in the request body. This enables a single-machine
            # token approach where the frontend can send the global token instead of
            # a Firebase id_token.
            try:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'token':
                    provided = parts[1]
                    env_token = os.environ.get('GLOBAL_API_TOKEN')
                    if env_token and provided == env_token:
                        # Expect frontend to pass 'email' in body when using global token
                        email = request.data.get('email')
                        if not email:
                            raise AuthenticationFailed('Global token provided but email missing in request body')
                        user, created = User.objects.get_or_create(username=email, defaults={'email': email})
                        if created:
                            user.set_unusable_password(); user.save(); logger.info(f"Created new user via global token: {user.username}")
                        drf_token, _ = Token.objects.get_or_create(user=user)
                        return Response({'token': drf_token.key, 'user': {'id': user.pk, 'username': user.username, 'email': getattr(user, 'email', None), 'created': created}}, status=status.HTTP_200_OK)
            except AuthenticationFailed:
                raise
            except Exception:
                # If the fallback also fails, return the original authentication failure
                raise AuthenticationFailed(f"Invalid Firebase token: {e}")
            # If no valid global token fallback, raise AuthenticationFailed
            raise AuthenticationFailed(f"Invalid Firebase token: {e}")

class FinancialSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        all_time = Transaction.objects.filter(user=user).annotate(month=TruncMonth('transaction_date')).values('month').annotate(income=Sum('amount', filter=Q(transaction_type='INC')), expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('month')
        this_month = Transaction.objects.filter(user=user, transaction_date__year=datetime.date.today().year, transaction_date__month=datetime.date.today().month).annotate(day=TruncDay('transaction_date')).values('day').annotate(income=Sum('amount', filter=Q(transaction_type='INC')), expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('day')
        return Response({'all_time': list(all_time), 'this_month': list(this_month)})
    
class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class WhoAmI(APIView):
    """Simple endpoint to verify token works and return current user info."""
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        return Response({'id': user.pk, 'username': user.username, 'email': getattr(user, 'email', None)})

class UpcomingBirthdaysView(APIView):
    def get(self, request, *args, **kwargs):
        today = datetime.date.today(); in_a_week = today + datetime.timedelta(days=7)
        today_doy = today.timetuple().tm_yday; week_later_doy = in_a_week.timetuple().tm_yday
        clients = Client.objects.filter(user=request.user).exclude(birthday__isnull=True).annotate(birthday_doy=Extract('birthday', 'doy'))
        if today_doy <= week_later_doy:
            upcoming = clients.filter(birthday_doy__gte=today_doy, birthday_doy__lte=week_later_doy)
        else:
            upcoming = clients.filter(Q(birthday_doy__gte=today_doy) | Q(birthday_doy__lte=week_later_doy))
        serializer = ClientSerializer(upcoming.order_by('birthday_doy'), many=True)
        return Response(serializer.data)

SCOPES = [ 'https://www.googleapis.com/auth/calendar',  'https://www.googleapis.com/auth/contacts.readonly']
def get_google_flow():
    return Flow.from_client_config( client_config={ "web": { "client_id": settings.GOOGLE_CLIENT_ID, "client_secret": settings.GOOGLE_CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "redirect_uris": [settings.GOOGLE_REDIRECT_URI], } }, scopes=SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI)
def _get_google_service(user, service_name, version):
    try:
        creds = GoogleCredentials.objects.get(user=user)
        credentials = Credentials( token=creds.access_token, refresh_token=creds.refresh_token, token_uri='https://oauth2.googleapis.com/token', client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET)
        if not credentials.valid or credentials.expired:
            try:
                credentials.refresh(Request())
                creds.access_token = credentials.token; creds.token_expiry = credentials.expiry; creds.save()
            except Exception as e:
                raise APIException(f"Failed to refresh Google token: {e}", code=status.HTTP_401_UNAUTHORIZED)
        return build(service_name, version, credentials=credentials)
    except GoogleCredentials.DoesNotExist:
        raise APIException("Google credentials not found for this user.", code=status.HTTP_401_UNAUTHORIZED)
class CheckGoogleAuthView(APIView):
    def get(self, request, *args, **kwargs):
        is_authenticated = GoogleCredentials.objects.filter(user=request.user).exists()
        return Response({'isAuthenticated': is_authenticated})
class GoogleCalendarInitView(APIView):
    def get(self, request, *args, **kwargs):
        flow = get_google_flow()
        state = get_random_string(length=32)
        OAuthState.objects.create(user=request.user, state=state)
        authorization_url, _ = flow.authorization_url( access_type='offline', include_granted_scopes='true', state=state, prompt='consent')
        return Response({'authorization_url': authorization_url})
class GoogleCalendarRedirectView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        state = request.query_params.get('state')
        try:
            oauth_state_obj = OAuthState.objects.get(state=state)
            user = oauth_state_obj.user; oauth_state_obj.delete() 
            flow = get_google_flow(); flow.fetch_token(code=request.query_params.get('code'))
            credentials = flow.credentials
            GoogleCredentials.objects.update_or_create( user=user, defaults={ 'access_token': credentials.token, 'refresh_token': credentials.refresh_token, 'token_expiry': credentials.expiry})
            return redirect(settings.FRONTEND_URL + '/calendar')
        except OAuthState.DoesNotExist:
            return redirect(settings.FRONTEND_URL + '/calendar?error=invalid_state')
class GoogleContactsListView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            service = _get_google_service(request.user, 'people', 'v1')
            results = service.people().connections().list( resourceName='people/me', personFields='names,emailAddresses,phoneNumbers', pageSize=500).execute()
            connections = results.get('connections', [])
            contact_list = []
            for person in connections:
                contact = {}
                if names := person.get('names', []): contact['name'] = names[0].get('displayName')
                if emails := person.get('emailAddresses', []): contact['email'] = emails[0].get('value')
                if phones := person.get('phoneNumbers', []): contact['phone'] = phones[0].get('value')
                if 'name' in contact: contact_list.append(contact)
            return Response(contact_list)
        except HttpError as e:
            raise APIException(f"Google API Error: {e.reason}", code=e.status_code)
class GoogleCalendarEventListView(APIView):
    def get(self, request, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        start, end = request.query_params.get('start'), request.query_params.get('end')
        events_result = service.events().list( calendarId='primary',  timeMin=start,  timeMax=end, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        formatted_events = [{'id': e['id'], 'title': e.get('summary', 'Без названия'), 'start': e['start'].get('dateTime', e['start'].get('date')), 'end': e['end'].get('dateTime', e['end'].get('date')), 'extendedProps': {'description': e.get('description', '')} } for e in events]
        return Response(formatted_events)
    def post(self, request, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        event_data = { 'summary': request.data.get('title'), 'description': request.data.get('description'), 'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'}, 'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'}, }
        event = service.events().insert(calendarId='primary', body=event_data).execute()
        return Response(event, status=status.HTTP_201_CREATED)
class GoogleCalendarEventDetailView(APIView):
    def put(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        event_data = { 'summary': request.data.get('title'), 'description': request.data.get('description'), 'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'}, 'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'}, }
        event = service.events().update(calendarId='primary', eventId=event_id, body=event_data).execute()
        return Response(event)
    def delete(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return Response(status=status.HTTP_204_NO_CONTENT)