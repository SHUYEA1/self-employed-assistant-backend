# Файл: backend/crm/urls.py (Полная, очищенная версия)

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClientViewSet, 
    InteractionViewSet, 
    TransactionViewSet, 
    TagViewSet, 
    TimeEntryViewSet,
    FinancialSummaryView, 
    RegisterView,
    GoogleCalendarInitView, 
    GoogleCalendarRedirectView, 
    CheckGoogleAuthView, 
    GoogleCalendarEventListView, 
    GoogleCalendarEventDetailView,
    UpcomingBirthdaysView,
    GoogleLoginView, 
    GoogleContactsListView 
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'time-entries', TimeEntryViewSet, basename='timeentry')

# Отдельная группа URL для календаря
calendar_urls = [
    path('auth/status/', CheckGoogleAuthView.as_view(), name='google-auth-status'),
    path('auth/init/', GoogleCalendarInitView.as_view(), name='google-calendar-init'),
    path('auth/callback/', GoogleCalendarRedirectView.as_view(), name='google-calendar-callback'),
    path('events/', GoogleCalendarEventListView.as_view(), name='google-calendar-event-list'),
    path('events/<str:event_id>/', GoogleCalendarEventDetailView.as_view(), name='google-calendar-event-detail'), 
]

# Отдельная группа URL для аутентификации
auth_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('google/', GoogleLoginView.as_view(), name='google-login'),
]

# Главный список маршрутов приложения crm
urlpatterns = [
    # 1. Все эндпоинты, созданные через DRF Router
    path('', include(router.urls)), 
    
    # 2. Кастомные эндпоинты приложения
    path('clients/birthdays/', UpcomingBirthdaysView.as_view(), name='upcoming-birthdays'),
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('google/contacts/', GoogleContactsListView.as_view(), name='google-contacts-list'),
    
    # 3. Подключение групп URL
    path('calendar/', include(calendar_urls)),
    path('auth/', include(auth_urls)),
]