from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, Interaction, Transaction, Tag # Добавили Tag

User = get_user_model()


# --- НОВЫЙ СЕРИАЛИЗАТОР ---
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'user']
        read_only_fields = ['user']


class ClientSerializer(serializers.ModelSerializer):
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    # Это поле будет показывать полную информацию о тегах при чтении данных
    tags = TagSerializer(many=True, read_only=True) 
    
    # А это поле будет принимать только ID тегов при записи (создании/обновлении)
    # write_only=True означает, что оно не будет отображаться при GET-запросах
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(), # DRF требует queryset, мы его отфильтруем во view
        source='tags', # Указываем, что это поле работает с модельным полем 'tags'
        write_only=True
    )

    class Meta:
        model = Client
        # Добавляем новые поля в список
        fields = [
            'id', 'name', 'email', 'phone', 'notes', 'user', 'created_at',
            'total_income', 'total_expense', 'status', 'birthday', 'tags', 'tag_ids'
        ]
        read_only_fields = ['user']

    # Переопределяем метод create, чтобы вручную привязать теги к клиенту
    def create(self, validated_data):
        # validated_data['tags'] содержит список объектов Tag
        # Мы используем .pop() чтобы извлечь теги из данных перед созданием клиента
        tags_data = validated_data.pop('tags', None)
        client = Client.objects.create(**validated_data)
        # Если теги были переданы, привязываем их
        if tags_data:
            client.tags.set(tags_data)
        return client

    # То же самое для метода update
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        # super().update() обновляет все остальные поля (name, email и т.д.)
        instance = super().update(instance, validated_data)
        # Если `tags_data` был передан (даже пустым списком), обновляем теги
        # Если он не был передан (None), мы теги не трогаем
        if tags_data is not None:
            instance.tags.set(tags_data)
        return instance


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