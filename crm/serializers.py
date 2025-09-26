from rest_framework import serializers
from django.contrib.auth import get_user_model

# Единый блок импорта моделей
from .models import Client, Interaction, Transaction, Tag, TimeEntry

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'user']
        read_only_fields = ['user']


class ClientSerializer(serializers.ModelSerializer):
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    tags = TagSerializer(many=True, read_only=True)
    
    # Поле для записи ID тегов, теперь необязательное
    tag_ids = serializers.PrimaryKeyRelatedField(
    many=True,
    queryset=Tag.objects.all(),
    source='tags', 
    write_only=True,
    required=False # <--- ЭТА СТРОКА ТОЧНО ЕСТЬ И СОХРАНЕНА
)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'notes', 'user', 'created_at',
            'total_income', 'total_expense', 'status', 'birthday', 'tags', 'tag_ids'
        ]
        read_only_fields = ['user']

    # Метод create был переписан некорректно в прошлых версиях, исправляем
    def create(self, validated_data):
        # `tags` уже были обработаны и помещены в validated_data по ключу `tags` 
        # благодаря `source='tags'` в поле `tag_ids`
        tags_data = validated_data.pop('tags', None)
        client = Client.objects.create(**validated_data)
        if tags_data:
            client.tags.set(tags_data)
        return client

    # Исправляем метод update по той же логике
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        # Если `tags_data` был передан (даже пустым списком), обновляем теги.
        if tags_data is not None:
            instance.tags.set(tags_data)
        return instance


class InteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interaction
        fields = [
            'id', 'client', 'interaction_type', 'interaction_date', 'description',
            'due_date', 'status', 'completed_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = ['id', 'user', 'client', 'client_name', 'amount', 'transaction_type', 'description', 'transaction_date']
        read_only_fields = ['user']


class TimeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeEntry
        fields = ['id', 'user', 'client', 'start_time', 'end_time', 'description', 'duration_seconds']
        read_only_fields = ['user', 'duration_seconds']


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
