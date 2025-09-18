from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet,
    FinancialSummaryView, RegisterView,
    GoogleCalendarInitView, GoogleCalendarRedirectView, GoogleCalendarEventsView,
    CheckGoogleAuthView
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'transactions', TransactionViewSet, basename='transaction')

calendar_urls = [
    path('auth/status/', CheckGoogleAuthView.as_view(), name='google-auth-status'),
    path('auth/init/', GoogleCalendarInitView.as_view(), name='google-calendar-init'),
    path('auth/callback/', GoogleCalendarRedirectView.as_view(), name='google-calendar-callback'),
    path('events/', GoogleCalendarEventsView.as_view(), name='google-calendar-events'),
]

urlpatterns = [
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('register/', RegisterView.as_view(), name='register'),
    path('calendar/', include(calendar_urls)),
    path('', include(router.urls)),
]