from django.contrib import admin
# Добавляем Tag и TimeEntry
from .models import Client, Interaction, Transaction, GoogleCredentials, Tag, TimeEntry

admin.site.register(Client)
admin.site.register(Interaction)
admin.site.register(Transaction)
admin.site.register(GoogleCredentials)
# --- НОВЫЕ СТРОКИ ---
admin.site.register(Tag)
admin.site.register(TimeEntry)