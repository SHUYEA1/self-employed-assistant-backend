import datetime
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.contrib.auth import get_user_model
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token

from .models import Client, Interaction, Transaction, Event
from .serializers import (
    ClientSerializer, InteractionSerializer, TransactionSerializer,
    EventSerializer, RegisterSerializer
)


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).annotate(
            total_income=Sum('transactions__amount', filter=Q(transactions__transaction_type='INC'), default=0.0),
            total_expense=Sum('transactions__amount', filter=Q(transactions__transaction_type='EXP'), default=0.0)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InteractionViewSet(viewsets.ModelViewSet):
    queryset = Interaction.objects.all()
    serializer_class = InteractionSerializer

    def get_queryset(self):
        queryset = Interaction.objects.filter(client__user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset

    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client and client.user != self.request.user:
            raise PermissionDenied("Вы не можете добавлять взаимодействия для чужих клиентов.")
        serializer.save()


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset

    def perform_create(self, serializer):
        client = serializer.validated_data.get('client')
        if client and client.user != self.request.user:
            raise PermissionDenied("Вы не можете добавлять транзакции для чужих клиентов.")
        serializer.save(user=self.request.user)


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EventsTodayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        today = datetime.date.today()
        events = Event.objects.filter(
            user=request.user,
            start_time__date=today
        ).order_by("start_time")
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class FinancialSummaryView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        today = datetime.date.today()

        all_time_summary = Transaction.objects.filter(user=user)\
            .annotate(month=TruncMonth('transaction_date')).values('month')\
            .annotate(income=Sum('amount', filter=Q(transaction_type='INC')),
                      expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('month')

        this_month_summary = Transaction.objects.filter(
            user=user,
            transaction_date__year=today.year,
            transaction_date__month=today.month
        ).annotate(day=TruncDay('transaction_date')).values('day')\
            .annotate(income=Sum('amount', filter=Q(transaction_type='INC')),
                      expense=Sum('amount', filter=Q(transaction_type='EXP'))).order_by('day')

        return Response({'all_time': list(all_time_summary), 'this_month': list(this_month_summary)})


class RegisterView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'token': token.key},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
