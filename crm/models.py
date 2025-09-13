# Файл: crm/models.py (Исправленная и очищенная версия)

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timezone import localdate  # <- Ключевой импорт для исправления

# Получаем модель пользователя, которую Django использует для аутентификации.
User = get_user_model()


class Client(models.Model):
    """Модель клиента."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Ответственный пользователь")
    name = models.CharField(max_length=200, verbose_name="Имя клиента")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['name']


class Interaction(models.Model):
    """Модель взаимодействия с клиентом."""
    class InteractionType(models.TextChoices):
        CALL = 'CALL', 'Звонок'
        MEETING = 'MEET', 'Встреча'
        EMAIL = 'MAIL', 'Email'
        OTHER = 'OTHR', 'Другое'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interactions', verbose_name="Клиент")
    interaction_type = models.CharField(
        max_length=4,
        choices=InteractionType.choices,
        default=InteractionType.CALL,
        verbose_name="Тип взаимодействия"
    )
    interaction_date = models.DateTimeField(default=timezone.now, verbose_name="Дата взаимодействия")
    description = models.TextField(verbose_name="Описание")

    def __str__(self):
        return f"{self.get_interaction_type_display()} с {self.client.name}"

    class Meta:
        verbose_name = "Взаимодействие"
        verbose_name_plural = "Взаимодействия"
        ordering = ['-interaction_date']


class Transaction(models.Model):
    """Модель финансовой операции (доход/расход)."""
    class TransactionType(models.TextChoices):
        INCOME = 'INC', 'Доход'
        EXPENSE = 'EXP', 'Расход'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    # 1. Добавлен related_name для лучшей практики
    client = models.ForeignKey(
        Client, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Клиент", 
        related_name='transactions' 
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    transaction_type = models.CharField(max_length=3, choices=TransactionType.choices, verbose_name="Тип операции")
    description = models.CharField(max_length=255, verbose_name="Описание")
    # 2. Главное исправление: default=localdate
    transaction_date = models.DateField(default=localdate, verbose_name="Дата операции")

    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.amount} ({self.description})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-transaction_date']


class Event(models.Model):
    """Модель события для календаря."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клиент")
    
    title = models.CharField(max_length=200, verbose_name="Название события")
    start_time = models.DateTimeField(verbose_name="Время начала")
    end_time = models.DateTimeField(verbose_name="Время окончания")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
        ordering = ['start_time']