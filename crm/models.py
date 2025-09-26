from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.timezone import localdate

User = get_user_model()

class OAuthState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class GoogleCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    access_token = models.CharField(max_length=2048)
    refresh_token = models.CharField(max_length=2048)
    token_expiry = models.DateTimeField()

    def __str__(self):
        return f"Google Credentials for {self.user.username}"

# --- НОВАЯ МОДЕЛЬ ---
class Tag(models.Model):
    """Модель для цветовых меток (тегов)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    name = models.CharField(max_length=50, verbose_name="Название тега")
    # Храним цвет в формате HEX, например, #FF5733
    color = models.CharField(max_length=7, default="#808080", verbose_name="Цвет")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        # У одного пользователя не может быть двух тегов с одинаковым названием
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name


class Client(models.Model):
    # --- НОВОЕ ПОЛЕ ---
    class ClientStatus(models.TextChoices):
        POTENTIAL = 'POT', 'Потенциальный'
        IN_PROGRESS = 'INP', 'В работе'
        DONE = 'DON', 'Завершено'
        CANCELED = 'CAN', 'Отказ'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Ответственный пользователь")
    name = models.CharField(max_length=200, verbose_name="Имя клиента")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    # --- НОВЫЕ ПОЛЯ ---
    status = models.CharField(
        max_length=3,
        choices=ClientStatus.choices,
        default=ClientStatus.POTENTIAL,
        verbose_name="Статус клиента"
    )
    birthday = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Теги")


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['name']


class Interaction(models.Model):
    class InteractionType(models.TextChoices):
        CALL = 'CALL', 'Звонок'
        MEETING = 'MEET', 'Встреча'
        EMAIL = 'MAIL', 'Email'
        OTHER = 'OTHR', 'Другое'

    # --- НОВЫЙ КЛАСС ДЛЯ СТАТУСОВ SLA ---
    class SLAStatus(models.TextChoices):
        PENDING = 'PEND', 'Ожидает'
        IN_PROGRESS = 'INP', 'В работе'
        COMPLETED = 'COMP', 'Выполнено'
        OVERDUE = 'OVRD', 'Просрочено'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interactions', verbose_name="Клиент")
    interaction_type = models.CharField(max_length=4, choices=InteractionType.choices, default=InteractionType.CALL, verbose_name="Тип взаимодействия")
    interaction_date = models.DateTimeField(default=timezone.now, verbose_name="Дата взаимодействия")
    description = models.TextField(verbose_name="Описание")

    # --- НОВЫЕ ПОЛЯ ДЛЯ SLA ---
    due_date = models.DateTimeField(blank=True, null=True, verbose_name="Срок выполнения")
    status = models.CharField(
        max_length=4,
        choices=SLAStatus.choices,
        default=SLAStatus.PENDING,
        verbose_name="Статус SLA"
    )
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата фактического выполнения")

    def __str__(self):
        return f"{self.get_interaction_type_display()} с {self.client.name}"

    class Meta:
        verbose_name = "Взаимодействие"
        verbose_name_plural = "Взаимодействия"
        ordering = ['-interaction_date']


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = 'INC', 'Доход'
        EXPENSE = 'EXP', 'Расход'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клиент", related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    transaction_type = models.CharField(max_length=3, choices=TransactionType.choices, verbose_name="Тип операции")
    description = models.CharField(max_length=255, verbose_name="Описание")
    transaction_date = models.DateField(default=localdate, verbose_name="Дата операции")

    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.amount} ({self.description})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-transaction_date']


# --- НОВАЯ МОДЕЛЬ ---
class TimeEntry(models.Model):
    """Модель для учета времени"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Клиент", related_name="time_entries")
    start_time = models.DateTimeField(verbose_name="Время начала")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Время окончания")
    description = models.CharField(max_length=255, blank=True, verbose_name="Описание")

    @property
    def duration_seconds(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def __str__(self):
        return f"Работа по клиенту {self.client.name} ({self.start_time.strftime('%Y-%m-%d')})"

    class Meta:
        verbose_name = "Запись времени"
        verbose_name_plural = "Записи времени"
        ordering = ['-start_time']
