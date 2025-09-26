from rest_framework import serializers
from .models import Project, Issue, Comment


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'issue', 'author', 'author_username', 'body', 'created_at']
        read_only_fields = ['author', 'created_at']


class IssueSerializer(serializers.ModelSerializer):
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = ['id', 'project', 'title', 'description', 'reporter', 'reporter_username', 'assignee', 'assignee_username', 'status', 'created_at', 'updated_at', 'comments']
        read_only_fields = ['reporter', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    issues = IssueSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'owner_username', 'created_at', 'issues']
        read_only_fields = ['owner', 'created_at']
