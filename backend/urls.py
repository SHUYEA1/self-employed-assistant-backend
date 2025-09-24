# Файл: backend/urls.py (Главный URL-конфигуратор)
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    # Обрати внимание, у входа и регистрации свой путь через /auth/
    path('api/auth/token/', obtain_auth_token, name='api_token_auth'),
    # Все остальные URL нашего приложения будут начинаться с /api/
    path('api/', include('crm.urls')),
]