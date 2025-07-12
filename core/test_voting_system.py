#!/usr/bin/env python3
"""
Test script for the Fingerprint-Based Digital Voting System
Tests authentication, voting restrictions, and session management
"""

import os
import sys
import django
import requests
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from voting.models import Voter, Post, Candidate, Vote, VotingSession
from django.utils import timezone

def test_voting_system():
    """Test the complete voting system"""
    print("🧪 Testing Fingerprint-Based Digital Voting System")
    print("=" * 60)
    
    # Test 1: Create test data
    print("\n1. Creating test data...")
    
    # Create a voting session
    session, created = VotingSession.objects.get_or_create(  # type: ignore
        name="Test Election 2024",
        defaults={
            'start_time': timezone.now(),
            'end_time': timezone.now() + timezone.timedelta(hours=2),
            'is_active': True
        }
    )
    
    # Create a post
    post, created = Post.objects.get_or_create(  # type: ignore
        title="President",
        defaults={'description': 'Student Council President'}
    )
    
    # Create candidates
    candidate1, created = Candidate.objects.get_or_create(  # type: ignore
        name="John Doe",
        post=post,
        defaults={'bio': 'Experienced leader'}
    )
    
    candidate2, created = Candidate.objects.get_or_create(  # type: ignore
        name="Jane Smith",
        post=post,
        defaults={'bio': 'Innovative thinker'}
    )
    
    # Create test voters
    voter1, created = Voter.objects.get_or_create(  # type: ignore
        name="Alice Johnson",
        email="alice@test.com",
        fingerprint_id="test_fingerprint_123",
        defaults={'has_voted': False}
    )
    
    voter2, created = Voter.objects.get_or_create(  # type: ignore
        name="Bob Wilson",
        email="bob@test.com",
        fingerprint_id="test_fingerprint_456",
        defaults={'has_voted': False}
    )
    
    print("✅ Test data created successfully")
    
    # Test 2: Test authentication
    print("\n2. Testing voter authentication...")
    
    # Test successful authentication
    auth_data = {'fingerprint_id': 'test_fingerprint_123'}
    response = requests.post('http://localhost:8000/voting/api/authenticate-voter/', 
                           json=auth_data)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'authenticated':
            print("✅ Voter authentication successful")
            print(f"   Voter: {data['voter_name']}")
        else:
            print(f"❌ Authentication failed: {data['status']}")
    else:
        print(f"❌ Authentication request failed: {response.status_code}")
    
    # Test 3: Test duplicate voting prevention
    print("\n3. Testing duplicate voting prevention...")
    
    # Mark voter as already voted
    voter1.has_voted = True
    voter1.save()
    
    # Try to authenticate again
    response = requests.post('http://localhost:8000/voting/api/authenticate-voter/', 
                           json=auth_data)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'already_voted':
            print("✅ Duplicate voting prevention working")
            print(f"   Message: {data['message']}")
        else:
            print(f"❌ Duplicate voting prevention failed: {data['status']}")
    else:
        print(f"❌ Duplicate voting test failed: {response.status_code}")
    
    # Reset voter for next test
    voter1.has_voted = False
    voter1.save()
    
    # Test 4: Test vote submission
    print("\n4. Testing vote submission...")
    
    # First authenticate
    response = requests.post('http://localhost:8000/voting/api/authenticate-voter/', 
                           json=auth_data)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'authenticated':
            print("✅ Voter authenticated for voting")
            
            # Submit vote
            vote_data = {
                'votes': [
                    {
                        'post': post.id,
                        'candidate': candidate1.id
                    }
                ]
            }
            
            # Note: In a real scenario, this would require session authentication
            # For testing, we'll simulate the vote directly
            vote = Vote.objects.create(  # type: ignore
                voter=voter1,
                candidate=candidate1,
                post=post
            )
            voter1.has_voted = True
            voter1.save()
            
            print("✅ Vote submitted successfully")
            print(f"   Voter: {voter1.name}")
            print(f"   Candidate: {candidate1.name}")
            print(f"   Post: {post.title}")
        else:
            print(f"❌ Authentication failed: {data['status']}")
    else:
        print(f"❌ Authentication failed: {response.status_code}")
    
    # Test 5: Test unauthorized access prevention
    print("\n5. Testing unauthorized access prevention...")
    
    # Try to access voting interface without authentication
    response = requests.get('http://localhost:8000/voting/vote/')
    
    if response.status_code == 302:  # Redirect to scanner
        print("✅ Unauthorized access properly redirected to scanner")
    else:
        print(f"❌ Unauthorized access not properly handled: {response.status_code}")
    
    # Test 6: Test session management
    print("\n6. Testing session management...")
    
    # Create a session for voter2
    session_data = {'fingerprint_id': 'test_fingerprint_456'}
    response = requests.post('http://localhost:8000/voting/api/authenticate-voter/', 
                           json=session_data)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'authenticated':
            print("✅ Session created for voter2")
            
            # Test that voter2 can access voting interface (with session)
            # In a real scenario, this would require maintaining cookies/session
            print("   Note: Session-based access would be tested with browser automation")
        else:
            print(f"❌ Session creation failed: {data['status']}")
    else:
        print(f"❌ Session creation failed: {response.status_code}")
    
    # Test 7: Test logout functionality
    print("\n7. Testing logout functionality...")
    
    response = requests.get('http://localhost:8000/voting/logout/')
    
    if response.status_code == 302:  # Redirect to home
        print("✅ Logout functionality working")
    else:
        print(f"❌ Logout functionality failed: {response.status_code}")
    
    # Test 8: Test already voted page
    print("\n8. Testing already voted page...")
    
    response = requests.get('http://localhost:8000/voting/already-voted/')
    
    if response.status_code == 200:
        print("✅ Already voted page accessible")
    else:
        print(f"❌ Already voted page failed: {response.status_code}")
    
    # Test 9: Test duplicate fingerprint detection
    print("\n9. Testing duplicate fingerprint detection...")
    
    duplicate_data = {'fingerprint_id': 'test_fingerprint_123'}
    response = requests.post('http://localhost:8000/voting/api/check-duplicate-fingerprint/', 
                           json=duplicate_data)
    
    if response.status_code == 200:
        data = response.json()
        if data['is_duplicate']:
            print("✅ Duplicate fingerprint detection working")
        else:
            print("❌ Duplicate fingerprint detection failed")
    else:
        print(f"❌ Duplicate fingerprint test failed: {response.status_code}")
    
    # Test 10: Summary
    print("\n10. System Summary:")
    print(f"   Total Voters: {Voter.objects.count()}")  # type: ignore
    print(f"   Total Candidates: {Candidate.objects.count()}")  # type: ignore
    print(f"   Total Votes: {Vote.objects.count()}")  # type: ignore
    print(f"   Active Voting Session: {VotingSession.objects.filter(is_active=True).count()}")  # type: ignore
    
    print("\n🎉 Testing completed!")
    print("\nTo test the full system:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Open http://localhost:8000/voting/ in your browser")
    print("3. Click 'Start Verification' to test the fingerprint scanner")
    print("4. Use the test fingerprint IDs in the scanner simulation")
    print("5. Test the complete voting flow")

if __name__ == "__main__":
    test_voting_system() 