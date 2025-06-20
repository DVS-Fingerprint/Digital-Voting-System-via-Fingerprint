from django.core.management.base import BaseCommand
from voting.models import Post, Candidate, Voter, VotingSession
from django.utils import timezone, dateparse

class Command(BaseCommand):
    help = 'Add demo data for Digital Voting System'

    def handle(self, *args, **options):
        # Create Posts
        post1, _ = Post.objects.get_or_create(title='President')  # type: ignore
        post2, _ = Post.objects.get_or_create(title='Vice President')  # type: ignore

        # Create Candidates
        c1, _ = Candidate.objects.get_or_create(name='Alice Johnson', post=post1)  # type: ignore
        c2, _ = Candidate.objects.get_or_create(name='Bob Smith', post=post1)  # type: ignore
        c3, _ = Candidate.objects.get_or_create(name='Carol Lee', post=post2)  # type: ignore
        c4, _ = Candidate.objects.get_or_create(name='David Kim', post=post2)  # type: ignore

        # Create Voters
        v1, _ = Voter.objects.get_or_create(name='John Doe', uid='F123456')  # type: ignore
        v2, _ = Voter.objects.get_or_create(name='Jane Roe', uid='F654321')  # type: ignore
        v3, _ = Voter.objects.get_or_create(name='Sam Patel', uid='F111222')  # type: ignore

        # Create an active voting session
        now = timezone.now()
        session, _ = VotingSession.objects.get_or_create(  # type: ignore
            start_time=now,
            end_time=now + timezone.timedelta(hours=2),
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS('Demo data added successfully!'))  # type: ignore 