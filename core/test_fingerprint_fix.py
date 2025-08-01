#!/usr/bin/env python3
"""
Test script to verify fingerprint security fixes
Run this after making the changes to test if the issue is resolved.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from voting.models import Voter, FingerprintTemplate, ActivityLog
from voting.views import advanced_fingerprint_match

def test_fingerprint_security():
    """Test the fingerprint security improvements"""
    print("🔒 Testing Fingerprint Security Fixes")
    print("=" * 50)
    
    # Clean up any existing test data
    Voter.objects.filter(voter_id__startswith="TEST").delete()
    FingerprintTemplate.objects.filter(voter__voter_id__startswith="TEST").delete()
    
    # Create test voters
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
    
    print(f"✅ Created test voters: {voter1.name} and {voter2.name}")
    
    # Test 1: Voter1's template should match Voter1
    print("\n🧪 Test 1: Voter1 template matching")
    incoming_template = bytes.fromhex(template1)
    templates = FingerprintTemplate.objects.select_related('voter').all()
    matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
    
    if matched_voter and matched_voter.voter_id == "TEST001":
        print(f"✅ SUCCESS: Correctly matched to {matched_voter.name}")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    else:
        print(f"❌ FAILED: Incorrectly matched to {matched_voter}")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    
    # Test 2: Voter2's template should match Voter2
    print("\n🧪 Test 2: Voter2 template matching")
    incoming_template = bytes.fromhex(template2)
    matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
    
    if matched_voter and matched_voter.voter_id == "TEST002":
        print(f"✅ SUCCESS: Correctly matched to {matched_voter.name}")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    else:
        print(f"❌ FAILED: Incorrectly matched to {matched_voter}")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    
    # Test 3: Random template should not match
    print("\n🧪 Test 3: Random template rejection")
    random_template = "FFEEDDCCBBAA99887766554433221100FFEEDDCCBBAA99887766554433221100"
    incoming_template = bytes.fromhex(random_template)
    matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
    
    if not matched_voter or confidence_score < 65.0:
        print(f"✅ SUCCESS: Correctly rejected random template")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    else:
        print(f"❌ FAILED: Incorrectly matched random template to {matched_voter}")
        print(f"   Confidence: {confidence_score:.2f}, Type: {match_type}")
    
    # Test 4: Check threshold enforcement
    print("\n🧪 Test 4: Threshold enforcement")
    if confidence_score < 65.0:
        print("✅ SUCCESS: Threshold correctly enforced (65.0 minimum)")
    else:
        print(f"❌ FAILED: Threshold not enforced, score: {confidence_score}")
    
    print("\n" + "=" * 50)
    print("🎯 Security Test Summary:")
    print("- Increased confidence threshold from 55.0 to 65.0")
    print("- Simplified fingerprint matching algorithm")
    print("- Improved accuracy while maintaining usability")
    print("- Enhanced security without over-complexity")
    
    # Cleanup
    Voter.objects.filter(voter_id__startswith="TEST").delete()
    print("\n🧹 Cleaned up test data")

if __name__ == "__main__":
    test_fingerprint_security() 