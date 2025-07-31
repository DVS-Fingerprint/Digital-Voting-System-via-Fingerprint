from django.core.management.base import BaseCommand
from voting.models import Voter


class Command(BaseCommand):
    help = 'Check if a voter exists and create one if needed'

    def add_arguments(self, parser):
        parser.add_argument('fingerprint_id', type=str, help='Fingerprint ID to check')

    def handle(self, *args, **options):
        fingerprint_id = options['fingerprint_id']
        
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)
            self.stdout.write(
                self.style.SUCCESS(f'Voter found: {voter.name} (ID: {voter.voter_id}, has_voted: {voter.has_voted})')
            )
        except Voter.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'Voter with fingerprint_id "{fingerprint_id}" not found. Creating one...')
            )
            
            # Create a new voter
            voter = Voter.objects.create(
                voter_id=fingerprint_id,
                name=f"Test Voter {fingerprint_id}",
                fingerprint_id=fingerprint_id,
                has_voted=False
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created voter: {voter.name} (ID: {voter.voter_id})')
            ) 