# Файл: crm/admin.py

from django.contrib import admin
from .models import Client, Interaction, Transaction, Event

# Регистрируем каждую модель в админ-панели.
# Самый простой способ - это просто передать класс модели в admin.site.register.

admin.site.register(Client)
admin.site.register(Interaction)
admin.site.register(Transaction)
admin.site.register(Event)