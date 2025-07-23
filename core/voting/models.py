from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class VotingSession(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)  # type: ignore

    def __str__(self):
        return f"Session: {self.start_time} - {self.end_time} ({'Active' if self.is_active else 'Inactive'})"

class Post(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class Voter(models.Model):
    name = models.CharField(max_length=255)
    uid = models.CharField(max_length=100, unique=True)  # Fingerprint UID
    has_voted = models.BooleanField(default=False)  # type: ignore
    last_vote_attempt = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Candidate(models.Model):
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='candidates/photos/', null=True, blank=True)
    symbol = models.ImageField(upload_to='candidates/symbols/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, help_text="Brief biography of the candidate")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='candidates')

    def __str__(self):
        return f"{self.name} ({self.post.title})"  # type: ignore

class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.voter.name} voted for {self.candidate.name} ({self.post.title})"  # type: ignore

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.timestamp}: {self.action}"
    
class FingerprintTemplate(models.Model):
    user_id = models.IntegerField()
    template_hex = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User {self.user_id} - Template at {self.created_at}"

