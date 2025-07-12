from django.core.management.base import BaseCommand
from voting.models import Post, Candidate, Voter, VotingSession
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Add demo data for testing'

    def handle(self, *args, **options):
        # Create posts
        president, _ = Post.objects.get_or_create(title='President')  # type: ignore
        vice_president, _ = Post.objects.get_or_create(title='Vice President')  # type: ignore
        secretary, _ = Post.objects.get_or_create(title='Secretary')  # type: ignore

        # Create candidates
        c1, _ = Candidate.objects.get_or_create(  # type: ignore
            name='Alice Johnson',
            post=president,
            bio='Experienced leader with 10 years of community service.'
        )
        c2, _ = Candidate.objects.get_or_create(  # type: ignore
            name='Bob Smith',
            post=president,
            bio='Innovative thinker with strong technical background.'
        )
        c3, _ = Candidate.objects.get_or_create(  # type: ignore
            name='Carol Davis',
            post=vice_president,
            bio='Dedicated team player with excellent communication skills.'
        )
        c4, _ = Candidate.objects.get_or_create(  # type: ignore
            name='David Wilson',
            post=secretary,
            bio='Organized and detail-oriented professional.'
        )

        # Create voters
        v1, _ = Voter.objects.get_or_create(  # type: ignore
            name='John Doe',
            email='john.doe@example.com',
            fingerprint_id='F123456'
        )
        v2, _ = Voter.objects.get_or_create(  # type: ignore
            name='Jane Roe',
            email='jane.roe@example.com',
            fingerprint_id='F654321'
        )
        v3, _ = Voter.objects.get_or_create(  # type: ignore
            name='Sam Patel',
            email='sam.patel@example.com',
            fingerprint_id='F111222'
        )

        # Create voting session
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=24)
        session, _ = VotingSession.objects.get_or_create(  # type: ignore
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully created demo data')
        ) 