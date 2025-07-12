from rest_framework import serializers
from .models import Voter, Post, Candidate, Vote, VotingSession, ActivityLog

class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ['id', 'name', 'email', 'fingerprint_id', 'has_voted', 'last_vote_attempt', 'created_at']

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'title']

class CandidateSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)
    photo = serializers.ImageField(required=False)
    symbol = serializers.ImageField(required=False)
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'photo', 'symbol', 'post', 'bio']

class VoteSerializer(serializers.ModelSerializer):
    voter = VoterSerializer(read_only=True)
    candidate = CandidateSerializer(read_only=True)
    post = PostSerializer(read_only=True)
    class Meta:
        model = Vote
        fields = ['id', 'voter', 'candidate', 'post', 'timestamp']

class VotingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VotingSession
        fields = ['id', 'start_time', 'end_time', 'is_active']

class ActivityLogSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'action', 'timestamp', 'details'] 