# Файл: crm/urls.py (новый файл)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet, InteractionViewSet, TransactionViewSet, EventViewSet, FinancialSummaryView
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet, 
    EventViewSet, FinancialSummaryView, RegisterView
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
# ... (остальные router.register без изменений)
router.register(r'interactions', InteractionViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'events', EventViewSet)


urlpatterns = [
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    # НОВЫЙ URL:
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]