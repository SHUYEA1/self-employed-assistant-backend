from django.contrib import admin
from .models import Client, Interaction, Transaction, GoogleCredentials

admin.site.register(Client)
admin.site.register(Interaction)
admin.site.register(Transaction)
admin.site.register(GoogleCredentials)