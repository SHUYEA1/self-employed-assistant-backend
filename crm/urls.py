# Файл: backend/crm/urls.py (Финальная, очищенная версия)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet, TagViewSet, TimeEntryViewSet,
    FinancialSummaryView, RegisterView,
    GoogleCalendarInitView, GoogleCalendarRedirectView, CheckGoogleAuthView,
    GoogleCalendarEventListView, GoogleCalendarEventDetailView,
    UpcomingBirthdaysView, GoogleLoginView, GoogleContactsListView,
    GenerateInvoicePDF # Убедимся, что он импортирован
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'time-entries', TimeEntryViewSet, basename='timeentry')
# Теги мы пока убрали, но эндпоинт можно оставить
router.register(r'tags', TagViewSet, basename='tag')


calendar_urls = [
    path('auth/status/', CheckGoogleAuthView.as_view(), name='google-auth-status'),
    path('init/', GoogleCalendarInitView.as_view(), name='google-calendar-init'), # <-- Убираем лишний 'auth/'
    path('callback/', GoogleCalendarRedirectView.as_view(), name='google-calendar-callback'), # <-- Убираем лишний 'auth/'
    path('events/', GoogleCalendarEventListView.as_view(), name='google-calendar-event-list'),
    path('events/<str:event_id>/', GoogleCalendarEventDetailView.as_view(), name='google-calendar-event-detail'),
]

auth_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('google/', GoogleLoginView.as_view(), name='google-login'),
]

urlpatterns = [
    # DRF Роутеры
    path('', include(router.urls)),

    # Кастомные эндпоинты
    path('clients/<int:client_id>/generate-invoice/', GenerateInvoicePDF.as_view(), name='generate-invoice'),
    path('birthdays/', UpcomingBirthdaysView.as_view(), name='upcoming-birthdays'), # Упрощенный URL
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('google/contacts/', GoogleContactsListView.as_view(), name='google-contacts-list'),

    # Группы
    path('calendar/', include(calendar_urls)),
    path('auth/', include(auth_urls)),
]