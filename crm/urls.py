from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet,
    EventViewSet, FinancialSummaryView, RegisterView, EventsTodayView
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet, basename='interaction')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'events', EventViewSet, basename='event')

urlpatterns = [
    path('events/today/', EventsTodayView.as_view(), name='events-today'),
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]