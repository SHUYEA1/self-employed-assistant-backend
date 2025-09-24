from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet, TagViewSet,
    FinancialSummaryView, RegisterView,
    GoogleCalendarInitView, GoogleCalendarRedirectView, CheckGoogleAuthView, 
    GoogleCalendarEventListView, GoogleCalendarEventDetailView,
    UpcomingBirthdaysView,
    # Импортируем новые view
    GoogleLoginView, GoogleContactsListView 
)
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet, TagViewSet, TimeEntryViewSet, # <-- Добавили
    # ...
)
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'time-entries', TimeEntryViewSet, basename='timeentry')

# Группируем URL для календаря
calendar_urls = [
    path('auth/status/', CheckGoogleAuthView.as_view(), name='google-auth-status'),
    path('auth/init/', GoogleCalendarInitView.as_view(), name='google-calendar-init'),
    path('auth/callback/', GoogleCalendarRedirectView.as_view(), name='google-calendar-callback'),
    path('events/', GoogleCalendarEventListView.as_view(), name='google-calendar-event-list'),
    # --- ИСПРАВЛЕННАЯ СТРОКА ---
    path('events/<str:event_id>/', GoogleCalendarEventDetailView.as_view(), name='google-calendar-event-detail'), 
]

# Группируем URL для аутентификации
auth_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('google/', GoogleLoginView.as_view(), name='google-login'),
]

urlpatterns = [
    # Все роутеры Django REST Framework
    path('', include(router.urls)), 
    path('clients/birthdays/', UpcomingBirthdaysView.as_view(), name='upcoming-birthdays'),
    
    # Кастомные эндпоинты
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('calendar/', include(calendar_urls)),
    
    path('google/contacts/', GoogleContactsListView.as_view(), name='google-contacts-list'),
    
    # Включаем группу URL для аутентификации
    path('auth/', include(auth_urls)),
]