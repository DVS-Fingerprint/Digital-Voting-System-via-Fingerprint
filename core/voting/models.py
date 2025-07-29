from django.db import models
from django.utils import timezone

class VotingSession(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"Session: {self.start_time} - {self.end_time} ({'Active' if self.is_active else 'Inactive'})"

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time and self.is_active

    class Meta:
        ordering = ['-start_time']


class Post(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['title']


class Voter(models.Model):
    voter_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    fingerprint_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    has_voted = models.BooleanField(default=False, db_index=True)
    last_vote_attempt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optionally add age and gender
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    def __str__(self):
        return f"{self.name} (Voter ID: {self.voter_id})"

    class Meta:
        ordering = ['name']


class Candidate(models.Model):
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='candidates/photos/', null=True, blank=True)
    symbol = models.ImageField(upload_to='candidates/symbols/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='candidates')

    def __str__(self):
        return f"{self.name} ({self.post.title})"

    class Meta:
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
        ordering = ['name']


class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.voter.name} voted for {self.candidate.name} ({self.post.title})"

    class Meta:
        unique_together = ('voter', 'post')
        ordering = ['-timestamp']


class ActivityLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.timestamp}: {self.action}"

    class Meta:
        ordering = ['-timestamp']


class FingerprintTemplate(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE, null=True, blank=True)
    template_hex = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.voter:
            return f"Voter {self.voter.voter_id} - Template at {self.created_at}"
        else:
            return f"Temporary Template at {self.created_at}"

    class Meta:
        ordering = ['-created_at']


class ScanTrigger(models.Model):
    voter_id = models.CharField(max_length=50, null=True, blank=True)
    action = models.CharField(max_length=20, choices=[("register", "Register"), ("match", "Match")])
    is_used = models.BooleanField(default=False, db_index=True)  # Prevent ESP32 repeating
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = 'used' if self.is_used else 'pending'
        return f"Trigger for voter_id={self.voter_id} - {self.action} ({status})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_used']),
            models.Index(fields=['created_at']),
        ]
