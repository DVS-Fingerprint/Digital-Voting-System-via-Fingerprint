from django.contrib import admin
from .models import Voter, Post, Candidate, Vote, VotingSession, ActivityLog
from .models import FingerprintTemplate

admin.site.register(FingerprintTemplate)

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('name', 'uid', 'has_voted', 'last_vote_attempt')
    search_fields = ('name', 'uid')

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title',)

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'post')
    search_fields = ('name',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'post')
        }),
        ('Media', {
            'fields': ('photo', 'symbol'),
            'classes': ('collapse',)
        }),
        ('Biography', {
            'fields': ('bio',),
            'description': 'Brief biography of the candidate (max 500 characters)'
        }),
    )

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'candidate', 'post', 'timestamp')
    search_fields = ('voter__name', 'candidate__name')

@admin.register(VotingSession)
class VotingSessionAdmin(admin.ModelAdmin):
    list_display = ('start_time', 'end_time', 'is_active')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp')
    search_fields = ('action', 'user__username')

