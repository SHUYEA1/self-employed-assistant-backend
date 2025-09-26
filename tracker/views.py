from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, APIException
from rest_framework.response import Response
from .models import Project, Issue, Comment
from .serializers import ProjectSerializer, IssueSerializer, CommentSerializer
import logging

logger = logging.getLogger(__name__)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Explicitly require authenticated user to avoid DB integrity errors
        if not self.request.user or not self.request.user.is_authenticated:
            logger.warning("Unauthenticated attempt to create Project")
            raise PermissionDenied("Authentication is required to create a project.")
        try:
            serializer.save(owner=self.request.user)
        except Exception as e:
            # Log full exception and raise a friendly API error instead of letting a 500 bubble up
            logger.exception("Failed to create Project")
            raise APIException("Failed to create project.")

    # permissions: all actions require authentication


class IssueViewSet(viewsets.ModelViewSet):
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Issue.objects.filter(project__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(issue__project__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
