# Файл: backend/crm/views.py (Полностью исправленная версия с логикой Google)

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
from rest_framework.autoken.models import Token 

from firebase_admin import auth as firebase_auth
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from weasyprint import HTML

from .models import Client, Interaction, Transaction, GoogleCredentials, OAuthState, Tag, TimeEntry
from .serializers import (
    ClientSerializer, InteractionSerializer, TransactionSerializer,
    RegisterSerializer, TagSerializer, TimeEntrySerializer
)

User = get_user_model()


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
        serializer.save(user=self.request.user) # Разрешаем создавать завершенные таймеры
        
    @action(detail=False, methods=['post'], url_path='toggle-timer')
    def toggle_timer(self, request, *args, **kwargs):
        client_id = request.data.get('client_id')
        if not client_id: return Response({'error': 'client_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            client = Client.objects.get(id=client_id, user=request.user)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)
        active_timer = TimeEntry.objects.filter(user=request.user, end_time__isnull=True).first()
        if active_timer:
            active_timer.end_time = timezone.now()
            active_timer.save()
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


# --- APIViews (остальные) ---

class GenerateInvoicePDF(APIView):
    # Эта View теперь будет работать, когда мы добавим шаблон
    def post(self, request, client_id, *args, **kwargs):
        try:
            client = Client.objects.get(id=client_id, user=request.user)
        except Client.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        items = request.data.get('items', [])
        if not isinstance(items, list) or not items:
            return Response({'error': 'Items list is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        total_amount = 0
        for item in items:
            try:
                item['price'] = float(item.get('price', 0))
                item['quantity'] = int(item.get('quantity', 1))
                item['total'] = item['price'] * item['quantity']
                total_amount += item['total']
            except (ValueError, TypeError):
                return Response({'error': 'Invalid data in items list.'}, status=status.HTTP_400_BAD_REQUEST)

        context = {
            'client': client, 'user': request.user, 'items': items, 'total_amount': total_amount,
            'invoice_number': f'CRM-{datetime.date.today().strftime("%y%m")}-{client.id}',
            'generation_date': datetime.date.today().strftime('%d.%m.%Y')
        }
        
        html_string = render_to_string('invoice_template.html', context)
        pdf_file = HTML(string=html_string).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice-{client.id}-{datetime.date.today()}.pdf"'
        return response

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
            if created: user.set_unusable_password(); user.save()
            drf_token, _ = Token.objects.get_or_create(user=user)
            return Response({'token': drf_token.key}, status=status.HTTP_200_OK)
        except Exception as e:
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


# --- НОВЫЙ БЛОК: ПОЛНАЯ РЕАЛИЗАЦАЯ ЛОГИКИ GOOGLE ---

SCOPES = [
    'https://www.googleapis.com/auth/calendar', 
    'https://www.googleapis.com/auth/contacts.readonly'
]

def get_google_flow():
    """Создает и возвращает экземпляр Flow для OAuth."""
    return Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE, # <-- Убедись, что этот путь прописан в settings.py
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

def _get_google_service(user, service_name, version):
    """Вспомогательная функция для получения Google API service."""
    try:
        creds = GoogleCredentials.objects.get(user=user)
        credentials = Credentials(
            token=creds.access_token,
            refresh_token=creds.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        if not credentials.valid or credentials.expired:
            try:
                credentials.refresh(Request())
                creds.access_token = credentials.token
                creds.token_expiry = credentials.expiry
                creds.save()
            except Exception as e:
                raise APIException(f"Failed to refresh Google token: {e}", code=status.HTTP_401_UNAUTHORIZED)
        
        return build(service_name, version, credentials=credentials)
    except GoogleCredentials.DoesNotExist:
        raise APIException("Google credentials not found for this user.", code=status.HTTP_401_UNAUTHORIZED)

class CheckGoogleAuthView(APIView):
    """Проверяет, есть ли у пользователя действительные учетные данные Google."""
    def get(self, request, *args, **kwargs):
        is_authenticated = GoogleCredentials.objects.filter(user=request.user).exists()
        return Response({'isAuthenticated': is_authenticated})

class GoogleCalendarInitView(APIView):
    """Инициирует процесс авторизации Google."""
    def get(self, request, *args, **kwargs):
        flow = get_google_flow()
        state = get_random_string(length=32)
        OAuthState.objects.create(user=request.user, state=state)
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent' # Важно для получения refresh_token
        )
        return Response({'authorization_url': authorization_url})

class GoogleCalendarRedirectView(APIView):
    """Обрабатывает редирект от Google после авторизации."""
    permission_classes = [AllowAny]
    def get(self, request, *args, **kwargs):
        state = request.query_params.get('state')
        try:
            oauth_state_obj = OAuthState.objects.get(state=state)
            user = oauth_state_obj.user
            oauth_state_obj.delete() # State используется один раз

            flow = get_google_flow()
            flow.fetch_token(code=request.query_params.get('code'))
            
            credentials = flow.credentials
            GoogleCredentials.objects.update_or_create(
                user=user,
                defaults={
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_expiry': credentials.expiry
                }
            )
            return redirect(settings.FRONTEND_URL + '/calendar')
        except OAuthState.DoesNotExist:
            return redirect(settings.FRONTEND_URL + '/calendar?error=invalid_state')

class GoogleContactsListView(APIView):
    """Получает список контактов Google."""
    def get(self, request, *args, **kwargs):
        try:
            service = _get_google_service(request.user, 'people', 'v1')
            results = service.people().connections().list(
                resourceName='people/me',
                personFields='names,emailAddresses,phoneNumbers',
                pageSize=500
            ).execute()
            connections = results.get('connections', [])
            
            contact_list = []
            for person in connections:
                contact = {}
                names = person.get('names', [])
                emails = person.get('emailAddresses', [])
                phones = person.get('phoneNumbers', [])
                
                if names: contact['name'] = names[0].get('displayName')
                if emails: contact['email'] = emails[0].get('value')
                if phones: contact['phone'] = phones[0].get('value')

                if 'name' in contact: contact_list.append(contact)
                    
            return Response(contact_list)
        except HttpError as e:
            raise APIException(f"Google API Error: {e.reason}", code=e.status_code)

class GoogleCalendarEventListView(APIView):
    """Получает или создает события в календаре."""
    def get(self, request, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start, 
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        formatted_events = [{
            'id': e['id'],
            'title': e.get('summary', 'Без названия'),
            'start': e['start'].get('dateTime', e['start'].get('date')),
            'end': e['end'].get('dateTime', e['end'].get('date')),
            'extendedProps': {'description': e.get('description', '')}
        } for e in events]
        return Response(formatted_events)

    def post(self, request, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        event_data = {
            'summary': request.data.get('title'),
            'description': request.data.get('description'),
            'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'},
            'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},
        }
        event = service.events().insert(calendarId='primary', body=event_data).execute()
        return Response(event, status=status.HTTP_201_CREATED)

class GoogleCalendarEventDetailView(APIView):
    """Обновляет или удаляет конкретное событие."""
    def put(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        event_data = {
            'summary': request.data.get('title'),
            'description': request.data.get('description'),
            'start': {'dateTime': request.data.get('start'), 'timeZone': 'UTC'},
            'end': {'dateTime': request.data.get('end'), 'timeZone': 'UTC'},
        }
        event = service.events().update(calendarId='primary', eventId=event_id, body=event_data).execute()
        return Response(event)

    def delete(self, request, event_id, *args, **kwargs):
        service = _get_google_service(request.user, 'calendar', 'v3')
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return Response(status=status.HTTP_204_NO_CONTENT)