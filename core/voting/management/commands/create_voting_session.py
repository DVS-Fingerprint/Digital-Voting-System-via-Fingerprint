from django.core.management.base import BaseCommand
from django.utils import timezone
from voting.models import VotingSession


class Command(BaseCommand):
    help = 'Create an active voting session for testing'

    def handle(self, *args, **options):
        # Deactivate any existing sessions
        VotingSession.objects.filter(is_active=True).update(is_active=False)
        
        # Create a new active session
        session = VotingSession.objects.create(
            name="Test Voting Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=24),
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created active voting session: {session.name} (ID: {session.id})')
        ) 