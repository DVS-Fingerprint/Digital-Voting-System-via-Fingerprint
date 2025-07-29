from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.utils.html import format_html
from .models import Voter, Post, Candidate, Vote, VotingSession, ActivityLog, FingerprintTemplate

admin.site.register(FingerprintTemplate)

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('voter_id', 'name', 'fingerprint_id', 'age', 'gender', 'has_voted', 'last_vote_attempt')
    search_fields = ('voter_id', 'name', 'fingerprint_id', 'age', 'gender')
    list_filter = ('has_voted', 'created_at')
    readonly_fields = ('created_at', 'last_vote_attempt')
    
    class Media:
        js = ('admin/js/fingerprint_polling.js',)
        css = {
            'all': ('admin/css/fingerprint_admin.css',)
        }
    
    def get_form(self, request, obj=None, change=False, **kwargs):  # fix signature to add change=False
        form = super().get_form(request, obj, change=change, **kwargs)
        if obj is None:  # Only for new voter creation
            if hasattr(form, 'base_fields') and 'fingerprint_id' in form.base_fields:
                form.base_fields['fingerprint_id'].widget.attrs.update({
                    'class': 'fingerprint-id-field',
                    'readonly': 'readonly',
                    'placeholder': 'Scan fingerprint to auto-fill this field...'
                })
        return form


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
    list_display = ('action', 'timestamp')
    search_fields = ('action',)
