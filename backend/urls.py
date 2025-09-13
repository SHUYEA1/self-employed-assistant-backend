# Файл: backend/urls.py (Исправленная версия)

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URL для получения токена (используем без дефиса для единообразия)
    path('api/token-auth/', obtain_auth_token, name='api_token_auth'),
    
    # Все остальные URL нашего API, начинающиеся с /api/
    path('api/', include('crm.urls')),
]