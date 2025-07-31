#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from voting.models import Voter, VotingSession, Post, Candidate

def setup_test_data():
    print("🔧 Setting up test data...")
    
    # 1. Create active voting session
    print("📊 Creating active voting session...")
    VotingSession.objects.filter(is_active=True).update(is_active=False)
    session = VotingSession.objects.create(
        name="Test Voting Session",
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(hours=24),
        is_active=True
    )
    print(f"✅ Created voting session: {session.name} (ID: {session.id})")
    
    # 2. Create test voter with TEMP_34 fingerprint
    print("👤 Creating test voter...")
    voter, created = Voter.objects.get_or_create(
        fingerprint_id="TEMP_34",
        defaults={
            'voter_id': 'TEMP_34',
            'name': 'Test Voter TEMP_34',
            'has_voted': False
        }
    )
    if created:
        print(f"✅ Created voter: {voter.name} (ID: {voter.voter_id})")
    else:
        print(f"✅ Found existing voter: {voter.name} (ID: {voter.voter_id})")
    
    # 3. Check if posts and candidates exist
    posts = Post.objects.all()
    candidates = Candidate.objects.all()
    print(f"📋 Found {posts.count()} posts and {candidates.count()} candidates")
    
    print("✅ Test data setup complete!")
    print(f"🔗 Dashboard URL: http://192.168.1.96:8000/dashboard/")
    print(f"🔗 Test voter can vote at: http://192.168.1.96:8000/cast-vote/TEMP_34/")

if __name__ == '__main__':
    setup_test_data() 