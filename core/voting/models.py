from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Election(models.Model):
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Voter(models.Model):
    full_name = models.CharField(max_length=255)
    voter_id = models.CharField(max_length=20, unique=True)
    fingerprint_id = models.CharField(max_length=100, unique=True)
    has_voted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.voter.full_name} voted for {self.candidate.name}"

class Candidate(models.Model):
    name = models.CharField(max_length=100)
    party = models.CharField(max_length=100)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.party}"

class Vote(models.Model):
    voter = models.OneToOneField(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.voter.name} voted for {self.candidate.name}"
