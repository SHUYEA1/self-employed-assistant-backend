from django.contrib import admin
from .models import Project, Issue, Comment


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'created_at')
    search_fields = ('name', 'owner__username')


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'project', 'reporter', 'assignee', 'status', 'created_at')
    list_filter = ('status', 'project')
    search_fields = ('title', 'description')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'issue', 'author', 'created_at')
    search_fields = ('body',)
