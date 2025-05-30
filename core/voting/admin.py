from django.contrib import admin
from .models import Voter, Candidate, Vote, Election

# Register your models here.

admin.site.register(Voter)
admin.site.register(Candidate)
admin.site.register(Vote)
admin.site.register(Election)
