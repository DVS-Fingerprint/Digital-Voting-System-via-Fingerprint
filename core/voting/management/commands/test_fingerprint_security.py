from django.core.management.base import BaseCommand
from voting.models import Voter, FingerprintTemplate, ActivityLog
from voting.views import advanced_fingerprint_match
import random
import string

class Command(BaseCommand):
    help = 'Test fingerprint security improvements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-scenario',
            type=str,
            choices=['false_positive', 'security_threshold', 'multiple_matches'],
            default='security_threshold',
            help='Test scenario to run'
        )

    def handle(self, *args, **options):
        scenario = options['test_scenario']
        
        if scenario == 'security_threshold':
            self.test_security_threshold()
        elif scenario == 'false_positive':
            self.test_false_positive_prevention()
        elif scenario == 'multiple_matches':
            self.test_multiple_matches_detection()

    def test_security_threshold(self):
        """Test that the new higher threshold prevents false matches"""
        self.stdout.write("🔒 Testing security threshold improvements...")
        
        # Create test voters with different fingerprint templates
        voter1 = Voter.objects.create(
            voter_id="TEST001",
            name="Test Voter 1",
            has_voted=False
        )
        
        voter2 = Voter.objects.create(
            voter_id="TEST002", 
            name="Test Voter 2",
            has_voted=False
        )
        
        # Create different fingerprint templates
        template1 = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"
        template2 = "112233445566778899AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00"
        
        FingerprintTemplate.objects.create(voter=voter1, template_hex=template1)
        FingerprintTemplate.objects.create(voter=voter2, template_hex=template2)
        
        # Test with voter1's template - should match voter1
        incoming_template = bytes.fromhex(template1)
        templates = FingerprintTemplate.objects.select_related('voter').all()
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if matched_voter and matched_voter.voter_id == "TEST001" and confidence_score >= 75.0:
            self.stdout.write(self.style.SUCCESS("✅ Correct match with high confidence"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Incorrect match or low confidence: {matched_voter}, score: {confidence_score}"))
        
        # Test with voter2's template - should match voter2
        incoming_template = bytes.fromhex(template2)
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if matched_voter and matched_voter.voter_id == "TEST002" and confidence_score >= 75.0:
            self.stdout.write(self.style.SUCCESS("✅ Correct match with high confidence"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Incorrect match or low confidence: {matched_voter}, score: {confidence_score}"))
        
        # Test with a completely different template - should not match
        random_template = ''.join(random.choices('0123456789ABCDEF', k=128))
        incoming_template = bytes.fromhex(random_template)
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if not matched_voter or confidence_score < 75.0:
            self.stdout.write(self.style.SUCCESS("✅ Correctly rejected random template"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Incorrectly matched random template: {matched_voter}, score: {confidence_score}"))

    def test_false_positive_prevention(self):
        """Test that the system prevents false positive matches"""
        self.stdout.write("🛡️ Testing false positive prevention...")
        
        # Create voters with similar but not identical templates
        voter1 = Voter.objects.create(
            voter_id="SIM001",
            name="Similar Voter 1",
            has_voted=False
        )
        
        voter2 = Voter.objects.create(
            voter_id="SIM002",
            name="Similar Voter 2", 
            has_voted=False
        )
        
        # Create templates that are similar but not identical
        template1 = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"
        template2 = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778898"  # One byte different
        
        FingerprintTemplate.objects.create(voter=voter1, template_hex=template1)
        FingerprintTemplate.objects.create(voter=voter2, template_hex=template2)
        
        # Test that each template matches its own voter, not the other
        templates = FingerprintTemplate.objects.select_related('voter').all()
        
        # Test voter1's template
        incoming_template = bytes.fromhex(template1)
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if matched_voter and matched_voter.voter_id == "SIM001":
            self.stdout.write(self.style.SUCCESS("✅ Voter1 template correctly matched to Voter1"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Voter1 template incorrectly matched to: {matched_voter}"))
        
        # Test voter2's template  
        incoming_template = bytes.fromhex(template2)
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if matched_voter and matched_voter.voter_id == "SIM002":
            self.stdout.write(self.style.SUCCESS("✅ Voter2 template correctly matched to Voter2"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Voter2 template incorrectly matched to: {matched_voter}"))

    def test_multiple_matches_detection(self):
        """Test that the system detects and rejects multiple high-confidence matches"""
        self.stdout.write("🔍 Testing multiple matches detection...")
        
        # Create voters with very similar templates
        voter1 = Voter.objects.create(
            voter_id="MULT001",
            name="Multiple Match Voter 1",
            has_voted=False
        )
        
        voter2 = Voter.objects.create(
            voter_id="MULT002",
            name="Multiple Match Voter 2",
            has_voted=False
        )
        
        # Create very similar templates that might cause multiple matches
        template1 = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"
        template2 = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"  # Identical
        
        FingerprintTemplate.objects.create(voter=voter1, template_hex=template1)
        FingerprintTemplate.objects.create(voter=voter2, template_hex=template2)
        
        # Test with the identical template - should detect multiple matches
        templates = FingerprintTemplate.objects.select_related('voter').all()
        incoming_template = bytes.fromhex(template1)
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        if match_type == "multiple_matches":
            self.stdout.write(self.style.SUCCESS("✅ Correctly detected multiple matches"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Failed to detect multiple matches: {match_type}"))
        
        self.stdout.write(f"Match result: {matched_voter}, Score: {confidence_score}, Type: {match_type}")

    def cleanup(self):
        """Clean up test data"""
        Voter.objects.filter(voter_id__startswith="TEST").delete()
        Voter.objects.filter(voter_id__startswith="SIM").delete()
        Voter.objects.filter(voter_id__startswith="MULT").delete()
        self.stdout.write("🧹 Cleaned up test data") 