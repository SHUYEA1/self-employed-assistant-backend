from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, Interaction, Transaction

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


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
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
            password=validated_data['password']
        )
        return user