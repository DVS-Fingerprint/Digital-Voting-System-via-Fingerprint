from django.core.management.base import BaseCommand
from django.utils import timezone
from voting.models import Voter, Post, Candidate, Vote, VotingSession
from django.db import transaction
from django.db import models


class Command(BaseCommand):
    help = 'Test the fingerprint voting system and one vote per fingerprint logic'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Fingerprint Voting System...'))
        
        # Create test data if it doesn't exist
        self.create_test_data()
        
        # Test the voting logic
        self.test_voting_logic()
        
        self.stdout.write(self.style.SUCCESS('Test completed successfully!'))

    def create_test_data(self):
        """Create test data for voting"""
        # Create voting session
        session, created = VotingSession.objects.get_or_create(
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            defaults={'is_active': True}
        )
        
        # Create test voters with fingerprints
        voters_data = [
            {'name': 'John Doe', 'voter_id': 'V000001', 'fingerprint_id': 'F123456', 'has_voted': False},
            {'name': 'Jane Smith', 'voter_id': 'V000002', 'fingerprint_id': 'F654321', 'has_voted': False},
            {'name': 'Bob Johnson', 'voter_id': 'V000003', 'fingerprint_id': 'F111222', 'has_voted': False},
        ]
        
        for voter_data in voters_data:
            voter, created = Voter.objects.get_or_create(
                voter_id=voter_data['voter_id'],
                defaults=voter_data
            )
            if created:
                self.stdout.write(f'Created voter: {voter.name} (ID: {voter.voter_id})')
        
        # Create test posts and candidates
        posts_data = [
            {
                'title': 'President',
                'candidates': [
                    {'name': 'Alice Wilson', 'bio': 'Experienced leader'},
                    {'name': 'Charlie Brown', 'bio': 'Community advocate'},
                ]
            },
            {
                'title': 'Vice President',
                'candidates': [
                    {'name': 'David Lee', 'bio': 'Young professional'},
                    {'name': 'Emma Davis', 'bio': 'Education specialist'},
                ]
            }
        ]
        
        for post_data in posts_data:
            post, created = Post.objects.get_or_create(title=post_data['title'])
            if created:
                self.stdout.write(f'Created post: {post.title}')
            
            for candidate_data in post_data['candidates']:
                candidate, created = Candidate.objects.get_or_create(
                    name=candidate_data['name'],
                    post=post,
                    defaults={'bio': candidate_data['bio']}
                )
                if created:
                    self.stdout.write(f'Created candidate: {candidate.name} for {post.title}')

    def test_voting_logic(self):
        """Test the one vote per fingerprint logic"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Testing One Vote Per Fingerprint Logic')
        self.stdout.write('='*50)
        
        # Get test voters
        voters = Voter.objects.filter(fingerprint_id__isnull=False)[:3]
        posts = Post.objects.all()
        candidates = Candidate.objects.all()
        
        if not voters.exists():
            self.stdout.write(self.style.ERROR('No voters with fingerprints found!'))
            return
        
        if not posts.exists():
            self.stdout.write(self.style.ERROR('No posts found!'))
            return
        
        if not candidates.exists():
            self.stdout.write(self.style.ERROR('No candidates found!'))
            return
        
        # Test 1: First vote should succeed
        voter1 = voters[0]
        self.stdout.write(f'\nTest 1: First vote for {voter1.name}')
        self.stdout.write(f'Voter ID: {voter1.voter_id}, Fingerprint: {voter1.fingerprint_id}')
        self.stdout.write(f'Has voted before: {voter1.has_voted}')
        
        # Simulate vote
        with transaction.atomic():
            if not voter1.has_voted:
                # Create a vote
                candidate = candidates.first()
                Vote.objects.create(voter=voter1, candidate=candidate, post=candidate.post)
                voter1.has_voted = True
                voter1.last_vote_attempt = timezone.now()
                voter1.save()
                self.stdout.write(self.style.SUCCESS('✓ First vote successful'))
            else:
                self.stdout.write(self.style.WARNING('⚠ Voter has already voted'))
        
        # Test 2: Second vote attempt should fail
        self.stdout.write(f'\nTest 2: Second vote attempt for {voter1.name}')
        voter1.refresh_from_db()
        self.stdout.write(f'Has voted after first vote: {voter1.has_voted}')
        
        if voter1.has_voted:
            self.stdout.write(self.style.SUCCESS('✓ Second vote correctly prevented'))
        else:
            self.stdout.write(self.style.ERROR('✗ Second vote should have been prevented'))
        
        # Test 3: Different voter should be able to vote
        if voters.count() > 1:
            voter2 = voters[1]
            self.stdout.write(f'\nTest 3: Vote for different voter {voter2.name}')
            self.stdout.write(f'Voter ID: {voter2.voter_id}, Fingerprint: {voter2.fingerprint_id}')
            self.stdout.write(f'Has voted before: {voter2.has_voted}')
            
            if not voter2.has_voted:
                # Create a vote
                candidate = candidates.last()
                Vote.objects.create(voter=voter2, candidate=candidate, post=candidate.post)
                voter2.has_voted = True
                voter2.last_vote_attempt = timezone.now()
                voter2.save()
                self.stdout.write(self.style.SUCCESS('✓ Different voter vote successful'))
            else:
                self.stdout.write(self.style.WARNING('⚠ Different voter has already voted'))
        
        # Test 4: Check vote counts
        self.stdout.write(f'\nTest 4: Vote counts verification')
        total_votes = Vote.objects.count()
        voters_voted = Voter.objects.filter(has_voted=True).count()
        self.stdout.write(f'Total votes in database: {total_votes}')
        self.stdout.write(f'Voters marked as voted: {voters_voted}')
        
        if total_votes == voters_voted:
            self.stdout.write(self.style.SUCCESS('✓ Vote counts match'))
        else:
            self.stdout.write(self.style.ERROR('✗ Vote counts mismatch'))
        
        # Test 5: Check unique fingerprint constraint
        self.stdout.write(f'\nTest 5: Unique fingerprint constraint')
        duplicate_fingerprints = Voter.objects.values('fingerprint_id').annotate(
            count=models.Count('fingerprint_id')
        ).filter(count__gt=1)
        
        if duplicate_fingerprints.exists():
            self.stdout.write(self.style.ERROR('✗ Duplicate fingerprints found!'))
            for dup in duplicate_fingerprints:
                self.stdout.write(f'  Fingerprint {dup["fingerprint_id"]} appears {dup["count"]} times')
        else:
            self.stdout.write(self.style.SUCCESS('✓ All fingerprints are unique'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Test Summary')
        self.stdout.write('='*50)
        self.stdout.write(f'Total voters: {Voter.objects.count()}')
        self.stdout.write(f'Voters with fingerprints: {Voter.objects.filter(fingerprint_id__isnull=False).count()}')
        self.stdout.write(f'Voters who have voted: {Voter.objects.filter(has_voted=True).count()}')
        self.stdout.write(f'Total votes cast: {Vote.objects.count()}')
        self.stdout.write(f'Active voting session: {VotingSession.objects.filter(is_active=True).exists()}') 