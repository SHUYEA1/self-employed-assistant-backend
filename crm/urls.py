from django.urls import path, include
from django.contrib import admin
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, InteractionViewSet, TransactionViewSet,
    EventViewSet, FinancialSummaryView, RegisterView, EventsTodayView
)
urlpatterns = [
    path('admin/', admin.site.urls),
    # другие пути
]
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'interactions', InteractionViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'events', EventViewSet)

urlpatterns = [
    path('finance/summary/', FinancialSummaryView.as_view(), name='finance-summary'),
    path('register/', RegisterView.as_view(), name='register'),
    path('events/today/', EventsTodayView.as_view(), name='events-today'),  # 👈 новый эндпоинт
    path('', include(router.urls)),
]
