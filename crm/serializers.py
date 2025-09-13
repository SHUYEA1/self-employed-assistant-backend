# Файл: crm/serializers.py (Полностью исправленная версия)

from rest_framework import serializers
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from .models import Client, Interaction, Transaction, Event

# --- ГЛАВНОЕ ИСПРАВЛЕНИЕ: определяем User ОДИН РАЗ вверху файла ---
User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'notes', 'user', 'created_at', 'total_income', 'total_expense']
        read_only_fields = ['user']

class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = ['id', 'user', 'client', 'client_name', 'amount', 'transaction_type', 'description', 'transaction_date']
        read_only_fields = ['user']

class EventSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, default=None)

    class Meta:
        model = Event
        fields = ['id', 'user', 'client', 'client_name', 'title', 'start_time', 'end_time', 'description']
        read_only_fields = ['user']


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации новых пользователей.
    """
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User # Теперь User здесь определен
        fields = ['username', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()
        
        Token.objects.create(user=user)
        
        return user