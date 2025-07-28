from django.shortcuts import render
from .models import Candidate, Voter, Vote, Post, VotingSession, FingerprintTemplate, ActivityLog
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .forms import VoterRegistrationForm
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .serializers import (
    VoterSerializer, PostSerializer, CandidateSerializer, VoteSerializer,
    VotingSessionSerializer, VoteRequestSerializer
)
from rest_framework.permissions import IsAdminUser
import json
import base64
from .fingerprint_matcher import fingerprint_matcher


@staff_member_required
def register_voter(request):
    success = False
    
    # Get the next available voter ID for display
    last_voter = Voter.objects.order_by('-voter_id').first()
    if last_voter:
        try:
            last_num = int(last_voter.voter_id.replace('V', ''))
            next_voter_id = f"V{last_num + 1:06d}"
        except ValueError:
            next_voter_id = "V000001"
    else:
        next_voter_id = "V000001"
    
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            # Auto-generate voter ID if not provided
            if not form.cleaned_data.get('voter_id'):
                form.instance.voter_id = next_voter_id
            
            voter = form.save()
            template_hex = form.cleaned_data.get('template_hex')
            if template_hex:
                # Check if fingerprint template already exists for this voter
                FingerprintTemplate.objects.filter(voter=voter).delete()  # Remove old template
                FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
                print(f"✅ Voter registered with fingerprint: {voter.name} (ID: {voter.voter_id})")
                
                # Clear pending template from session
                request.session.pop('pending_template', None)
                request.session.pop('pending_voter_id', None)
            else:
                print(f"⚠️ Voter registered without fingerprint: {voter.name} (ID: {voter.voter_id})")
            
            success = True
            form = VoterRegistrationForm()  # Reset form after success
            # Re-calculate next voter ID after successful registration
            last_voter = Voter.objects.order_by('-voter_id').first()
            if last_voter:
                try:
                    last_num = int(last_voter.voter_id.replace('V', ''))
                    next_voter_id = f"V{last_num + 1:06d}"
                except ValueError:
                    next_voter_id = "V000001"
            else:
                next_voter_id = "V000001"
    else:
        # Check for pending template in session
        pending_template = request.session.get('pending_template')
        pending_voter_id = request.session.get('pending_voter_id')
        
        initial_data = {'voter_id': next_voter_id}
        if pending_template:
            initial_data['template_hex'] = pending_template
        
        # Pre-fill the voter_id field with the next available ID
        form = VoterRegistrationForm(initial=initial_data)
    
    context = {
        'form': form, 
        'success': success,
        'next_voter_id': next_voter_id,
        'has_pending_template': bool(request.session.get('pending_template'))
    }
    return render(request, 'voting/register_voter.html', context)

@staff_member_required
def admin_dashboard(request):
    total_voters = Voter.objects.count()  # type: ignore
    total_candidates = Candidate.objects.count()  # type: ignore
    total_votes = Vote.objects.count()  # type: ignore
    # Vote counts by candidate
    vote_counts = Candidate.objects.annotate(num_votes=Count('vote')).order_by('-num_votes')  # type: ignore
    context = {
        'total_voters': total_voters,
        'total_candidates': total_candidates,
        'total_votes': total_votes,
        'vote_counts': vote_counts,
    }
    return render(request, 'voting/admin_dashboard.html', context)

def home(request):
    return render(request, 'voting/home.html')

def voter_home(request):
    # For development, just show the page without auth
    return render(request, 'voting/voter_home.html')

def candidate_list(request):
    posts = Post.objects.prefetch_related('candidates').all()  # type: ignore
    return render(request, 'voting/candidate_list.html', {'posts': posts})

@api_view(['GET'])
def posts_list(request):
    posts = Post.objects.all()  # type: ignore
    serializer = PostSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def candidates_list(request):
    post_id = request.GET.get('post_id')
    candidates = Candidate.objects.select_related('post').all()  # type: ignore
    if post_id:
        candidates = candidates.filter(post_id=post_id)
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@api_view(['POST'])
def vote_view(request):
    """Accepts selected candidate IDs, stores vote. Requires session-based authentication."""
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        ActivityLog.objects.create(action='Vote attempt without authentication')
        return Response({'detail': 'Authentication required. No authenticated_voter_id in session.'}, status=401)
    serializer = VoteRequestSerializer(data=request.data)
    if not serializer.is_valid():
        ActivityLog.objects.create(action=f'Invalid vote data by voter_id={voter_id}: {serializer.errors}')
        return Response({'detail': 'Invalid vote data', 'errors': serializer.errors}, status=400)
    try:
        with transaction.atomic():
            voter = Voter.objects.select_for_update().get(id=voter_id)  # type: ignore
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Double voting attempt by voter_id={voter_id}')
                return Response({'detail': 'Already voted.'}, status=400)
            # Check voting session
            session = VotingSession.objects.filter(is_active=True).first()  # type: ignore
            if not session:
                ActivityLog.objects.create(action=f'Vote attempt outside session by voter_id={voter_id}')
                return Response({'detail': 'Voting is not active.'}, status=403)
            votes = serializer.validated_data['votes']
            for vote_item in votes:
                post_id = vote_item['post']
                candidate_id = vote_item['candidate']
                post = Post.objects.get(id=post_id)  # type: ignore
                candidate = Candidate.objects.get(id=candidate_id, post=post)  # type: ignore
                Vote.objects.create(voter=voter, candidate=candidate, post=post)  # type: ignore
            voter.has_voted = True
            voter.last_vote_attempt = timezone.now()
            voter.save()
            ActivityLog.objects.create(action=f'Successful vote by voter_id={voter_id}')
        # Clear session after voting
        request.session.pop('authenticated_voter_id', None)
        return Response({'detail': 'Vote cast successfully.', 'name': voter.name, 'timestamp': voter.last_vote_attempt})
    except Voter.DoesNotExist:  # type: ignore
        ActivityLog.objects.create(action=f'Vote attempt by non-existent voter_id={voter_id}')
        return Response({'detail': 'Voter not found.', 'voter_id': voter_id}, status=404)
    except Exception as e:
        ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
        return Response({'detail': f'Vote error: {str(e)}', 'voter_id': voter_id}, status=400)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def results_view(request):
    posts = Post.objects.prefetch_related('candidates__vote_set').all()  # type: ignore
    results = []
    for post in posts:
        candidates = post.candidates.all()  # uses prefetch_related
        candidate_results = []
        for candidate in candidates:
            votes = candidate.vote_set.count()  # uses prefetched vote_set
            candidate_results.append({
                'candidate': CandidateSerializer(candidate).data,
                'votes': votes
            })
        results.append({'post': PostSerializer(post).data, 'candidates': candidate_results})
    return Response(results)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def register_candidate(request):
    serializer = CandidateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_view(request):
    total_voters = Voter.objects.count()  # type: ignore
    total_votes = Vote.objects.count()  # type: ignore
    total_candidates = Candidate.objects.count()  # type: ignore
    session = VotingSession.objects.filter(is_active=True).first()  # type: ignore
    data = {
        'total_voters': total_voters,
        'total_votes': total_votes,
        'total_candidates': total_candidates,
        'voting_session': VotingSessionSerializer(session).data if session else None,
    }
    return Response(data)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@api_view(['POST'])
def authenticate_fingerprint(request):
    """ESP32 sends fingerprint template, returns voter status using similarity matching."""
    try:
        template_hex = request.data.get('template_hex')
        if not template_hex:
            return Response({'error': 'template_hex is required'}, status=400)
        
        # Use similarity-based matching
        match_result = fingerprint_matcher.find_best_match(template_hex)
        
        if match_result:
            voter, confidence = match_result
            print(f"✅ Fingerprint match found: {voter.name} (confidence: {confidence:.2f})")
            
            if voter.has_voted:
                return Response({
                    'status': 'already_voted', 
                    'name': voter.name,
                    'confidence': round(confidence, 3)
                }, status=200)
            else:
                return Response({
                    'status': 'ok', 
                    'name': voter.name,
                    'confidence': round(confidence, 3)
                }, status=200)
        else:
            print("❌ No fingerprint match found")
            return Response({'status': 'not_found'}, status=404)
            
    except Exception as e:
        print(f"❌ Error in authenticate_fingerprint: {e}")
        return Response({'error': str(e)}, status=500)

# Simplified fingerprint API endpoints



@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def check_duplicate_fingerprint(request):
    """Check if fingerprint ID already exists in database"""
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        
        # Check if fingerprint ID already exists
        is_duplicate = Voter.objects.filter(fingerprint_id=fingerprint_id).exists()  # type: ignore
        
        return JsonResponse({
            'status': 'success',
            'is_duplicate': is_duplicate,
            'message': 'Fingerprint already registered' if is_duplicate else 'Fingerprint is unique'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def verify_fingerprint(request):
    """Verify if a fingerprint template matches a specific voter."""
    try:
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        voter_id = data.get('voter_id')
        
        if not template_hex or not voter_id:
            return JsonResponse({'error': 'Missing template_hex or voter_id.'}, status=400)
        
        # Verify fingerprint
        is_match, confidence = fingerprint_matcher.verify_fingerprint(template_hex, voter_id)
        
        return JsonResponse({
            'status': 'success',
            'is_match': is_match,
            'confidence': round(confidence, 3),
            'threshold': fingerprint_matcher.similarity_threshold
        })
        
    except Exception as e:
        print(f"❌ Error in verify_fingerprint: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def match_fingerprint(request):
    """Find all potential matches for a fingerprint template."""
    try:
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        min_confidence = data.get('min_confidence', 0.7)
        
        if not template_hex:
            return JsonResponse({'error': 'Missing template_hex.'}, status=400)
        
        # Find multiple matches
        matches = fingerprint_matcher.find_multiple_matches(template_hex, min_confidence)
        
        results = []
        for voter, confidence in matches:
            results.append({
                'voter_id': voter.id,
                'voter_name': voter.name,
                'voter_id_display': voter.voter_id,
                'has_voted': voter.has_voted,
                'confidence': round(confidence, 3)
            })
        
        return JsonResponse({
            'status': 'success',
            'matches': results,
            'total_matches': len(results)
        })
        
    except Exception as e:
        print(f"❌ Error in match_fingerprint: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def fingerprint_statistics(request):
    """Get fingerprint matching statistics."""
    try:
        stats = fingerprint_matcher.get_template_statistics()
        return Response(stats)
    except Exception as e:
        print(f"❌ Error getting fingerprint statistics: {e}")
        return Response({'error': str(e)}, status=500)

def scanner(request):
    # Render the scanner page for fingerprint verification
    return render(request, 'voting/scanner.html')

# @fingerprint_required
def election_view(request):
    posts = Post.objects.prefetch_related('candidates').all()  # type: ignore
    if request.method == 'POST':
        # Logic to handle vote submission will go here
        return redirect('voting:thankyou')
    return render(request, 'voting/election.html', {'posts': posts})

def thankyou(request):
    # Example: show choices summary (replace with real logic)
    choices = request.session.get('choices', [])
    return render(request, 'voting/confirmation.html', {'choices': choices})

def already_voted(request):
    """Show message when voter has already voted"""
    voter_id = request.session.get('authenticated_voter_id')
    voter = None
    if voter_id:
        try:
            voter = Voter.objects.get(id=voter_id)  # type: ignore
        except Voter.DoesNotExist:  # type: ignore
            pass
    return render(request, 'voting/already_voted.html', {'voter': voter})



@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def authenticate_voter(request):
    """Authenticate voter via fingerprint and create session"""
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            ActivityLog.objects.create(action='Authentication attempt with missing fingerprint_id')
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)  # type: ignore
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Authentication attempt by already voted voter_id={voter.id}')
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'You have already voted',
                    'voter_name': voter.name
                })
            # Create session for authenticated voter
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            ActivityLog.objects.create(action=f'Authentication success for voter_id={voter.id}')
            return JsonResponse({
                'status': 'authenticated',
                'message': 'Voter authenticated successfully',
                'voter_name': voter.name,
                'redirect_url': '/voting/vote/'
            })
        except Voter.DoesNotExist:  # type: ignore
            ActivityLog.objects.create(action=f'Authentication attempt with invalid fingerprint_id={fingerprint_id}')
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint ID'
            })
    except json.JSONDecodeError:
        ActivityLog.objects.create(action='Authentication attempt with invalid JSON')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        ActivityLog.objects.create(action=f'Authentication error: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
# @fingerprint_required
def submit_vote(request):
    """Submit vote with authentication check (session-based)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        ActivityLog.objects.create(action='Vote attempt without authentication')
        return JsonResponse({'error': 'Authentication required. No authenticated_voter_id in session.'}, status=401)
    try:
        serializer = VoteRequestSerializer(data=json.loads(request.body))
        if not serializer.is_valid():
            ActivityLog.objects.create(action=f'Invalid vote data by voter_id={voter_id}: {serializer.errors}')
            return JsonResponse({'error': 'Invalid vote data', 'errors': serializer.errors}, status=400)
        with transaction.atomic():
            voter = Voter.objects.select_for_update().get(id=voter_id)  # type: ignore
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Double voting attempt by voter_id={voter_id}')
                return JsonResponse({'error': 'Already voted.'}, status=400)
            votes = serializer.validated_data['votes']
            # Check voting session
            session = VotingSession.objects.filter(is_active=True).first()  # type: ignore
            if not session:
                ActivityLog.objects.create(action=f'Vote attempt outside session by voter_id={voter_id}')
                return JsonResponse({'error': 'Voting is not active.'}, status=403)
            for vote_item in votes:
                post_id = vote_item.get('post')
                candidate_id = vote_item.get('candidate')
                if not post_id or not candidate_id:
                    continue
                try:
                    post = Post.objects.get(id=post_id)  # type: ignore
                    candidate = Candidate.objects.get(id=candidate_id, post=post)  # type: ignore
                    Vote.objects.create(voter=voter, candidate=candidate, post=post)  # type: ignore
                except (Post.DoesNotExist, Candidate.DoesNotExist) as e:  # type: ignore
                    ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
                    continue
            voter.has_voted = True
            voter.last_vote_attempt = timezone.now()
            voter.save()
            ActivityLog.objects.create(action=f'Successful vote by voter_id={voter_id}')
        # Clear session after voting
        request.session.pop('authenticated_voter_id', None)
        return JsonResponse({
            'status': 'success',
            'message': 'Vote submitted successfully',
            'voter_name': voter.name
        })
    except Voter.DoesNotExist:  # type: ignore
        ActivityLog.objects.create(action=f'Vote attempt by non-existent voter_id={voter_id}')
        return JsonResponse({'error': 'Voter not found.', 'voter_id': voter_id}, status=404)
    except json.JSONDecodeError:
        ActivityLog.objects.create(action=f'Invalid JSON in vote by voter_id={voter_id}')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
        return JsonResponse({'error': f'Vote error: {str(e)}', 'voter_id': voter_id}, status=500)

def logout_voter(request):
    """Logout voter and clear session"""
    request.session.pop('authenticated_voter_id', None)
    return redirect('voting:home')

# Add these new views after the existing views

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def trigger_scan(request):
    """Admin triggers fingerprint scan for registration or matching"""
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'register' or 'match'
        voter_id = data.get('voter_id')  # Only for registration
        
        if action not in ['register', 'match']:
            return JsonResponse({'error': 'Invalid action. Use "register" or "match".'}, status=400)
        
        if action == 'register' and not voter_id:
            return JsonResponse({'error': 'voter_id required for registration'}, status=400)
        
        # Store the scan trigger in session or cache
        request.session['scan_trigger'] = {
            'action': action,
            'voter_id': voter_id,
            'timestamp': timezone.now().isoformat()
        }
        request.session.modified = True
        
        print(f"🔍 Scan triggered: {action} for voter_id={voter_id}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Scan triggered for {action}',
            'action': action,
            'voter_id': voter_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  # Required for ESP32 hardware GETs (no CSRF token support)
@require_http_methods(["GET"])
def get_scan_trigger(request):
    """ESP32 polls this endpoint to check for scan triggers"""
    try:
        scan_trigger = request.session.get('scan_trigger')
        
        if not scan_trigger:
            return JsonResponse({
                'status': 'no_trigger',
                'message': 'No scan trigger active'
            })
        
        # Check if trigger is still valid (within 5 minutes)
        trigger_time = timezone.datetime.fromisoformat(scan_trigger['timestamp'])
        if timezone.now() - trigger_time > timezone.timedelta(minutes=5):
            # Clear expired trigger
            request.session.pop('scan_trigger', None)
            return JsonResponse({
                'status': 'expired',
                'message': 'Scan trigger expired'
            })
        
        return JsonResponse({
            'status': 'trigger_active',
            'action': scan_trigger['action'],
            'voter_id': scan_trigger['voter_id'],
            'message': f"Scan required for {scan_trigger['action']}"
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
def upload_template(request):
    """Updated upload_template to handle both registration and matching flows"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            voter_id = data.get('voter_id')  # For registration flow
            template_b64 = data.get('template')  # Changed from template_hex to template
            
            print(f"📥 Received template for voter_id: {voter_id}")
            print(f"📦 Template size: {len(template_b64) if template_b64 else 0} chars")

            if not template_b64:
                return JsonResponse({'error': 'template is required'}, status=400)

            # Decode base64 string to bytes
            template_bytes = base64.b64decode(template_b64)
            template_hex = template_bytes.hex()

            if voter_id:
                # Registration flow - store template in session for form population
                try:
                    # Store the template in session for the registration form
                    request.session['pending_template'] = template_hex
                    request.session['pending_voter_id'] = voter_id
                    request.session.modified = True
                    
                    print(f"✅ Template stored in session for voter_id: {voter_id}")
                    
                    # Clear the scan trigger
                    request.session.pop('scan_trigger', None)
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Template captured successfully for registration',
                        'voter_id': voter_id,
                        'template_hex': template_hex
                    })
                except Exception as e:
                    return JsonResponse({'error': f'Error storing template: {str(e)}'}, status=500)
            else:
                # Matching flow - create temporary storage
                temp_voter = Voter.objects.create(
                    voter_id=f"TEMP_{int(timezone.now().timestamp())}",
                    name=f"Temporary User {int(timezone.now().timestamp())}",
                    fingerprint_id=str(int(timezone.now().timestamp()))
                )
                FingerprintTemplate.objects.create(
                    voter=temp_voter,
                    template_hex=template_hex
                )
                print(f"✅ Template saved for temporary voter: {temp_voter.name}")

                return JsonResponse({'status': 'success'})
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)





@csrf_exempt  # Required for ESP32 hardware GETs (no CSRF token support)
@require_http_methods(["GET"])
def check_pending_template(request):
    """Check if there's a pending template in session for registration"""
    try:
        pending_template = request.session.get('pending_template')
        pending_voter_id = request.session.get('pending_voter_id')
        
        if pending_template:
            return JsonResponse({
                'status': 'success',
                'has_template': True,
                'template_hex': pending_template,
                'voter_id': pending_voter_id
            })
        else:
            return JsonResponse({
                'status': 'success',
                'has_template': False
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def scanner_authenticate(request):
    """Authenticate voter for scanner page using fingerprint template from ESP32"""
    try:
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        
        if not template_hex:
            return JsonResponse({'error': 'template_hex is required'}, status=400)
        
        # Use similarity-based matching
        match_result = fingerprint_matcher.find_best_match(template_hex)
        
        if match_result:
            voter, confidence = match_result
            print(f"✅ Scanner authentication successful: {voter.name} (confidence: {confidence:.2f})")
            
            if voter.has_voted:
                return JsonResponse({
                    'status': 'already_voted', 
                    'name': voter.name,
                    'confidence': round(confidence, 3)
                })
            
            # Set session for authenticated voter
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            
            return JsonResponse({
                'status': 'ok', 
                'name': voter.name,
                'confidence': round(confidence, 3)
            })
        else:
            print("❌ Scanner authentication failed: no match found")
            return JsonResponse({'status': 'not_found'}, status=404)
            
    except Exception as e:
        print(f"❌ Error in scanner_authenticate: {e}")
        return JsonResponse({'error': str(e)}, status=500)
