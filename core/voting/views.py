from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .forms import VoterRegistrationForm
from rest_framework import status, permissions, generics, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .serializers import (
    VoterSerializer, PostSerializer, CandidateSerializer, VoteSerializer,
    VotingSessionSerializer, VoteRequestSerializer
)
from rest_framework.permissions import IsAdminUser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import FingerprintTemplate, ActivityLog, ScanTrigger
import base64
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from .models import Voter, Candidate, Vote, Post, VotingSession
from django.utils import timezone


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Voter, FingerprintTemplate
from .forms import VoterRegistrationForm

@staff_member_required
def register_voter(request):
    success = False

    # Check if there's a current voter_id in session
    current_voter_id = request.session.get('current_voter_id')

    # If no current voter ID, generate the next one and create placeholder
    if not current_voter_id:
        last_voter = Voter.objects.order_by('-voter_id').first()
        if last_voter:
            try:
                last_num = int(last_voter.voter_id.replace('V', ''))
                current_voter_id = f"V{last_num + 1:06d}"
            except ValueError:
                current_voter_id = "V000001"
        else:
            current_voter_id = "V000001"
        
        # Create placeholder voter if it doesn't exist
        if not Voter.objects.filter(voter_id=current_voter_id).exists():
            Voter.objects.create(
                voter_id=current_voter_id,
                name="Placeholder Voter",
                fingerprint_id=None,
                has_voted=False
            )
        # Save in session
        request.session['current_voter_id'] = current_voter_id

    # Try to get voter instance; if not found, clear session and retry
    try:
        voter = Voter.objects.get(voter_id=current_voter_id)
    except Voter.DoesNotExist:
        request.session.pop('current_voter_id', None)
        return redirect('/register-voter/')

    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST, instance=voter)
        if form.is_valid():
            voter = form.save()
            success = True
    else:
        # On GET, pre-fill form with current voter data
        form = VoterRegistrationForm(instance=voter)

    context = {
        'form': form,
        'success': success,
        'next_voter_id': current_voter_id,
        'has_pending_template': True  # Always allow registration since we removed template requirement
    }

    return render(request, 'voting/register_voter.html', context)

@staff_member_required
def admin_dashboard(request):
    total_voters = Voter.objects.count()
    total_candidates = Candidate.objects.count()
    total_votes = Vote.objects.count()
    vote_counts = Candidate.objects.annotate(num_votes=Count('vote')).order_by('-num_votes')
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
    """Render the voter home page for authenticated voters"""
    voter_id = request.session.get('authenticated_voter_id')
    voter = None
    
    if voter_id:
        try:
            voter = Voter.objects.get(id=voter_id)
            if voter.has_voted:
                return redirect('/already-voted/')
        except Voter.DoesNotExist:
            pass
    
    return render(request, 'voting/voter_home.html', {'voter': voter})

def candidate_list(request):
    posts = Post.objects.prefetch_related('candidates').all()
    return render(request, 'voting/candidate_list.html', {'posts': posts})


@api_view(['GET'])
def posts_list(request):
    posts = Post.objects.all()
    serializer = PostSerializer(posts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def candidates_list(request):
    post_id = request.GET.get('post_id')
    candidates = Candidate.objects.select_related('post').all()
    if post_id:
        candidates = candidates.filter(post_id=post_id)
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def vote_view(request):
    """Accepts selected candidate IDs, stores vote. Requires session-based authentication."""
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        ActivityLog.objects.create(action='Vote attempt without authentication')
        return Response({'detail': 'Authentication required.'}, status=401)
    
    try:
        voter = Voter.objects.get(id=voter_id)
        if voter.has_voted:
            ActivityLog.objects.create(action=f'Double voting attempt by voter_id={voter_id}')
            return Response({'detail': 'Already voted.'}, status=400)
        
        votes = request.data.get('votes', [])
        if not votes:
            return Response({'detail': 'No votes provided.'}, status=400)
        
        session = VotingSession.objects.filter(is_active=True).first()
        if not session:
            ActivityLog.objects.create(action=f'Vote attempt outside session by voter_id={voter_id}')
            return Response({'detail': 'Voting is not active.'}, status=403)
        
        for vote_item in votes:
            post_id = vote_item.get('post')
            candidate_id = vote_item.get('candidate')
            if not post_id or not candidate_id:
                continue
            try:
                post = Post.objects.get(id=post_id)
                candidate = Candidate.objects.get(id=candidate_id, post=post)
                Vote.objects.create(voter=voter, candidate=candidate, post=post)
            except (Post.DoesNotExist, Candidate.DoesNotExist) as e:
                ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
                continue
        
        voter.has_voted = True
        voter.last_vote_attempt = timezone.now()
        voter.save()
        ActivityLog.objects.create(action=f'Successful vote by voter_id={voter_id}')
        
        return Response({'detail': 'Vote cast successfully.', 'name': voter.name, 'timestamp': voter.last_vote_attempt})
        
    except Voter.DoesNotExist:
        ActivityLog.objects.create(action=f'Vote attempt by non-existent voter_id={voter_id}')
        return Response({'detail': 'Voter not found.', 'voter_id': voter_id}, status=404)
    except Exception as e:
        ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
        return Response({'detail': f'Vote error: {str(e)}', 'voter_id': voter_id}, status=400)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def results_view(request):
    posts = Post.objects.prefetch_related('candidates__vote_set').all()
    results = []
    for post in posts:
        candidates = post.candidates.all()
        candidate_results = []
        for candidate in candidates:
            votes = candidate.vote_set.count()  # uses prefetched vote_set
            candidate_results.append({
                'candidate': CandidateSerializer(candidate).data,
                'votes': votes
            })
        results.append({
            'post': PostSerializer(post).data,
            'candidates': candidate_results
        })
    return Response(results)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def register_candidate(request):
    # Implementation for candidate registration
    pass


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_view(request):
    total_voters = Voter.objects.count()
    total_votes = Vote.objects.count()
    total_candidates = Candidate.objects.count()
    session = VotingSession.objects.filter(is_active=True).first()
    data = {
        'total_voters': total_voters,
        'total_votes': total_votes,
        'total_candidates': total_candidates,
        'voting_session': VotingSessionSerializer(session).data if session else None,
    }
    return Response(data)


@api_view(['POST'])
def authenticate_fingerprint(request):
    """ESP32 sends fingerprint template, returns voter status using advanced similarity matching."""
    try:
        template_hex = request.data.get('template_hex')
        if not template_hex:
            return Response({'error': 'template_hex is required'}, status=400)
        
        # Convert hex to bytes for comparison
        try:
            incoming_template = bytes.fromhex(template_hex)
        except Exception:
            return Response({'error': 'Invalid template_hex format'}, status=400)
        
        # Use advanced fingerprint matching algorithm
        templates = FingerprintTemplate.objects.select_related('voter').all()
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        # Strict threshold for security
        MINIMUM_CONFIDENCE_THRESHOLD = 55.0
        
        if matched_voter and confidence_score >= MINIMUM_CONFIDENCE_THRESHOLD:
            # Check if voter has already voted
            if matched_voter.has_voted:
                ActivityLog.objects.create(
                    action=f'Authentication attempt by already voted voter: {matched_voter.name} (ID: {matched_voter.voter_id})'
                )
                return Response({
                    'status': 'already_voted',
                    'message': 'You have already voted',
                    'voter_name': matched_voter.name,
                    'score': confidence_score,
                    'match_type': match_type
                })
            
            # Log successful authentication
            ActivityLog.objects.create(
                action=f'Fingerprint authentication successful: {matched_voter.name} (ID: {matched_voter.voter_id}) - Score: {confidence_score:.2f}'
            )
            
            return Response({
                'status': 'authenticated',
                'voter_id': matched_voter.voter_id,
                'voter_name': matched_voter.name,
                'score': confidence_score,
                'match_type': match_type,
                'confidence_level': 'high' if confidence_score >= 70.0 else 'medium'
            })
        else:
            # Log failed authentication attempt
            ActivityLog.objects.create(
                action=f'Fingerprint authentication failed - Best score: {confidence_score:.2f}, Match type: {match_type}'
            )
            
            return Response({
                'status': 'not_found',
                'message': 'No matching fingerprint found with sufficient confidence',
                'score': confidence_score,
                'match_type': match_type
            }, status=404)
          
    except Exception as e:
        ActivityLog.objects.create(action=f'Fingerprint authentication error: {str(e)}')
        print(f"❌ Error in authenticate_fingerprint: {e}")
        return Response({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def fingerprint_scan(request):
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        return JsonResponse({
            'status': 'success',
            'message': 'Fingerprint scan received',
            'fingerprint_id': fingerprint_id
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_duplicate_fingerprint(request):
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        is_duplicate = Voter.objects.filter(fingerprint_id=fingerprint_id).exists()
        return JsonResponse({
            'status': 'success',
            'is_duplicate': is_duplicate,
            'message': 'Fingerprint already registered' if is_duplicate else 'Fingerprint is unique'
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_latest_fingerprint(request):
    """Get the most recent fingerprint scan for admin form auto-fill"""
    latest = FingerprintTemplate.objects.order_by('-created_at').first()
    if latest:
        return JsonResponse({
            'status': 'ok',
            'fingerprint_id': latest.voter.fingerprint_id if latest.voter else None,
            'template_hex': latest.template_hex,
            'created_at': latest.created_at,
        })
    else:
        return JsonResponse({
            'status': 'no_scan',
            'fingerprint_id': None,
            'template_hex': None,
            'message': 'No fingerprint scans found'
        })


@csrf_exempt
@require_http_methods(["POST"])
def verify_fingerprint(request):
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)
            if voter.has_voted:
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'Voter has already cast their vote',
                    'voter_name': voter.name,
                    'redirect_url': None
                })
            else:
                return JsonResponse({
                    'status': 'verified',
                    'message': 'Voter verified successfully',
                    'voter_name': voter.name,
                    'redirect_url': '/vote/'
                })
        except Voter.DoesNotExist:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint ID',
                'redirect_url': None
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def scanner(request):
    # Render the scanner page for fingerprint verification
    return render(request, 'voting/scanner.html')


def election_view(request):
    posts = Post.objects.prefetch_related('candidates').all()
    if request.method == 'POST':
        return redirect('voting:thankyou')
    return render(request, 'voting/election.html', {'posts': posts})


def thankyou(request):
    choices = request.session.get('choices', [])
    return render(request, 'voting/confirmation.html', {'choices': choices})


def already_voted(request):
    voter_id = request.session.get('authenticated_voter_id')
    voter = None
    if voter_id:
        try:
            voter = Voter.objects.get(id=voter_id)
        except Voter.DoesNotExist:
            pass
    return render(request, 'voting/already_voted.html', {'voter': voter})


def dashboard(request):
    from .models import Post
    posts = Post.objects.prefetch_related('candidates').all()
    session_countdown = 300
    return render(request, 'voting/election.html', {'posts': posts, 'session_countdown': session_countdown})


@csrf_exempt
@require_http_methods(["POST"])
def authenticate_voter(request):
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)
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
                'message': 'Authentication successful',
                'voter_id': voter.id,
                'voter_name': voter.name,
                'redirect_url': '/vote/'
            })
        except Voter.DoesNotExist:
            ActivityLog.objects.create(action=f'Authentication attempt with invalid fingerprint_id={fingerprint_id}')
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint ID',
                'redirect_url': None
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
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
            voter = Voter.objects.select_for_update().get(id=voter_id)
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Double voting attempt by voter_id={voter_id}')
                return JsonResponse({'error': 'Already voted.'}, status=400)
            votes = serializer.validated_data['votes']
            # Check voting session
            session = VotingSession.objects.filter(is_active=True).first()
            if not session:
                ActivityLog.objects.create(action=f'Vote attempt outside session by voter_id={voter_id}')
                return JsonResponse({'error': 'Voting is not active.'}, status=403)
            for vote_item in votes:
                post_id = vote_item.get('post')
                candidate_id = vote_item.get('candidate')
                if not post_id or not candidate_id:
                    continue
                try:
                    post = Post.objects.get(id=post_id)
                    candidate = Candidate.objects.get(id=candidate_id, post=post)
                    Vote.objects.create(voter=voter, candidate=candidate, post=post)
                except (Post.DoesNotExist, Candidate.DoesNotExist) as e:
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
    except Voter.DoesNotExist:
        ActivityLog.objects.create(action=f'Vote attempt by non-existent voter_id={voter_id}')
        return JsonResponse({'error': 'Voter not found.', 'voter_id': voter_id}, status=404)
    except json.JSONDecodeError:
        ActivityLog.objects.create(action=f'Invalid JSON in vote by voter_id={voter_id}')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        ActivityLog.objects.create(action=f'Vote error for voter_id={voter_id}: {str(e)}')
        return JsonResponse({'error': f'Vote error: {str(e)}', 'voter_id': voter_id}, status=500)


def logout_voter(request):
    request.session.pop('authenticated_voter_id', None)
    return redirect('voting:home')



@csrf_exempt
@require_http_methods(["POST"])
def trigger_scan(request):
    """Admin triggers fingerprint scan for registration or matching"""
    print(f"🔍 Trigger scan called with method: {request.method}")
    print(f"🔍 Request body: {request.body}")
    print(f"🔍 Request headers: {dict(request.headers)}")
    
    try:
        data = json.loads(request.body)
        voter_id = data.get("voter_id")
        action = data.get("action")
        
        print(f"🔍 Parsed data - voter_id: {voter_id}, action: {action}")

        if action not in ["register", "match"]:
            print(f"❌ Invalid action: {action}")
            return JsonResponse({"error": "Invalid action"}, status=400)

        if action == "register":
            if not voter_id:
                print(f"❌ Missing voter_id for register action")
                return JsonResponse({"error": "voter_id required for registration"}, status=400)
            # New check: voter must exist before allowing registration trigger
            if not Voter.objects.filter(voter_id=voter_id).exists():
                print(f"❌ Voter ID {voter_id} does not exist, cannot create register trigger")
                return JsonResponse({"error": "Voter does not exist for this voter_id"}, status=400)

        # Mark any previous unused triggers as used to prevent duplicates
        print(f"🔄 Marking previous unused triggers as used...")
        ScanTrigger.objects.filter(used=False).update(used=True)
        
        # Create new scan trigger
        print(f"✅ Creating new trigger with voter_id={voter_id}, action={action}")
        trigger = ScanTrigger.objects.create(
            voter_id=voter_id if voter_id else None,
            action=action,
            used=False
        )

        # Log the scan trigger action (optional)
        ActivityLog.objects.create(action=f"Scan trigger created for voter ID {voter_id} ({action})")

        print(f"✅ Trigger created successfully with ID: {trigger.id}")
        return JsonResponse({
            "status": "success",
            "message": "Scan trigger created",
            "trigger_id": trigger.id
        })

    except Exception as e:
        print(f"❌ Error in trigger_scan: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
 
@require_GET
def get_scan_trigger(request):
    """ESP32 polls this endpoint to check for scan triggers"""
    try:
        print(f"🔍 ESP32 polling for scan trigger...")

        # Get the latest unused trigger
        trigger = ScanTrigger.objects.filter(used=False).order_by('-created_at').first()

        if trigger:
            print(f"✅ Found trigger: voter_id={trigger.voter_id}, action={trigger.action}, id={trigger.id}")

            # ✅ Include 'id' in response so ESP32 can mark it used later
            return JsonResponse({
                "id": trigger.id,
                "action": trigger.action,
                "voter_id": trigger.voter_id
            })
        else:
            print(f"❌ No unused triggers found")
            # Show recent triggers for debugging
            all_triggers = ScanTrigger.objects.all().order_by('-created_at')[:5]
            print(f"🔍 Recent triggers: {[f'ID:{t.id}, voter_id:{t.voter_id}, action:{t.action}, used:{t.used}' for t in all_triggers]}")

            return JsonResponse({"action": None, "voter_id": None, "id": None})
    except Exception as e:
        print(f"❌ Error in get_scan_trigger: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

    
@csrf_exempt
@require_http_methods(["POST"])
def mark_trigger_used(request):
    """Mark a scan trigger as used after ESP32 processes it"""
    try:
        data = json.loads(request.body)
        trigger_id = data.get("id")
        if not trigger_id:
            return JsonResponse({"error": "trigger id required"}, status=400)
        
        trigger = ScanTrigger.objects.get(id=trigger_id)
        trigger.used = True
        trigger.save()
        
        print(f"✅ Trigger {trigger_id} marked as used.")
        return JsonResponse({"status": "success"})
    except ScanTrigger.DoesNotExist:
        return JsonResponse({"error": "Trigger not found"}, status=404)
    
@csrf_exempt
@require_http_methods(["GET", "POST"])
def upload_template(request):
    """Upload fingerprint template for registration"""
    try:
        if request.method == "GET":
            return JsonResponse({
                'status': 'info',
                'message': 'This endpoint accepts POST requests with template_hex or template (base64) and voter_id',
                'example': {
                    'template_hex': 'your_template_hex_data',
                    'voter_id': 'optional_voter_id'
                }
            })

        data = json.loads(request.body)
        print(f"📥 Received upload_template POST data: {data}")

        template_b64 = data.get('template') or data.get('template_b64')
        template_hex = data.get('template_hex')
        voter_id = data.get('voter_id', '').strip()

        if template_b64 and not template_hex:
            try:
                template_hex = base64.b64decode(template_b64).hex()
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': 'Invalid base64 data'}, status=400)

        if not template_hex:
            return JsonResponse({'status': 'error', 'message': 'No template provided'}, status=400)

        # Validate template quality
        if not validate_fingerprint_template(template_hex):
            return JsonResponse({
                'status': 'error', 
                'message': 'Invalid or low-quality fingerprint template. Please scan again.'
            }, status=400)
        
        # Calculate template quality score
        quality_score = calculate_template_quality(template_hex)
        if quality_score < 30.0:
            return JsonResponse({
                'status': 'error', 
                'message': f'Template quality too low ({quality_score:.1f}/100). Please scan again with better finger placement.'
            }, status=400)

        if voter_id:
            try:
                print(f"🔍 Looking for voter_id: {voter_id}")
                voter = Voter.objects.get(voter_id__iexact=voter_id)
                
                # Delete old templates for this voter
                FingerprintTemplate.objects.filter(voter=voter).delete()
                
                # Create new template with quality info
                template = FingerprintTemplate.objects.create(
                    voter=voter, 
                    template_hex=template_hex
                )
                
                # Log template creation with quality score
                ActivityLog.objects.create(
                    action=f'Fingerprint template created for voter {voter_id} - Quality: {quality_score:.1f}/100'
                )
                
                print(f"✅ Created FingerprintTemplate for voter {voter_id} (Quality: {quality_score:.1f})")

                trigger = ScanTrigger.objects.filter(voter_id=voter_id, used=False).order_by('-created_at').first()
                if trigger:
                    trigger.used = True
                    trigger.save()
                    print(f"✅ Marked trigger as used for voter_id={voter_id}")

                return JsonResponse({
                    'status': 'success',
                    'quality_score': quality_score,
                    'message': f'Template stored successfully (Quality: {quality_score:.1f}/100)'
                })
            except Voter.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Voter not found'}, status=400)
        else:
            temp_template = FingerprintTemplate.objects.create(
                voter=None,
                template_hex=template_hex
            )
            print(f"🗃️ Created temporary FingerprintTemplate with id {temp_template.id} (Quality: {quality_score:.1f})")
            return JsonResponse({
                'status': 'success',
                'template_id': temp_template.id,
                'quality_score': quality_score,
                'message': f'Template stored successfully (Quality: {quality_score:.1f}/100)'
            })

    except Exception as e:
        print("❌ Error:", str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_protect
@require_http_methods(["POST"])
def register_voter_with_fingerprint(request):
    """Register a new voter and their fingerprint template."""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        email = data.get('email')
        template_hex = data.get('template_hex')
        if not (name and email and template_hex):
            return JsonResponse({'error': 'Missing required fields (name, email, template_hex).'}, status=400)
        if Voter.objects.filter(email=email).exists():
            return JsonResponse({'error': 'A voter with this email already exists.'}, status=400)
        voter = Voter.objects.create(name=name, email=email)
        FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
        return JsonResponse({'status': 'success', 'voter_id': voter.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
@require_http_methods(["POST"])
def fingerprint_authenticate(request):
    """Authenticate a voter by fingerprint template using advanced matching."""
    try:
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        if not template_hex:
            return JsonResponse({'error': 'Missing template_hex.'}, status=400)
        
        # Convert hex to bytes for comparison
        try:
            incoming_template = bytes.fromhex(template_hex)
        except Exception:
            return JsonResponse({'error': 'Invalid template_hex format.'}, status=400)
        
        # Use advanced fingerprint matching algorithm
        templates = FingerprintTemplate.objects.select_related('voter').all()
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)
        
        # Strict threshold for security
        MINIMUM_CONFIDENCE_THRESHOLD = 55.0
        
        if matched_voter and confidence_score >= MINIMUM_CONFIDENCE_THRESHOLD:
            if matched_voter.has_voted:
                ActivityLog.objects.create(
                    action=f'Authentication attempt by already voted voter: {matched_voter.name} (ID: {matched_voter.voter_id})'
                )
                return JsonResponse({
                    'status': 'already_voted', 
                    'voter_name': matched_voter.name,
                    'score': confidence_score,
                    'match_type': match_type
                })
            
            # Set session for authenticated voter
            request.session['authenticated_voter_id'] = matched_voter.id
            request.session.modified = True
            
            # Log successful authentication
            ActivityLog.objects.create(
                action=f'Fingerprint authentication successful: {matched_voter.name} (ID: {matched_voter.voter_id}) - Score: {confidence_score:.2f}'
            )
            
            return JsonResponse({
                'status': 'authenticated', 
                'voter_id': matched_voter.id, 
                'voter_name': matched_voter.name,
                'score': confidence_score,
                'match_type': match_type,
                'confidence_level': 'high' if confidence_score >= 70.0 else 'medium'
            })
        else:
            # Log failed authentication attempt
            ActivityLog.objects.create(
                action=f'Fingerprint authentication failed - Best score: {confidence_score:.2f}, Match type: {match_type}'
            )
            
            return JsonResponse({
                'error': 'Fingerprint not recognized with sufficient confidence.',
                'score': confidence_score,
                'match_type': match_type
            }, status=404)
            
    except Exception as e:
        ActivityLog.objects.create(action=f'Fingerprint authentication error: {str(e)}')
        return JsonResponse({'error': str(e)}, status=500)


def calculate_similarity(template1: bytes, template2: bytes) -> float:
    """
    Advanced fingerprint similarity calculation using multiple algorithms.
    Returns similarity score between 0 and 100.
    Uses Hamming distance, pattern matching, and feature comparison.
    """
    if not template1 or not template2:
        return 0.0

    # Ensure templates are the same length for comparison
    if len(template1) != len(template2):
        return 0.0
    
    # Method 1: Hamming Distance (bit-level comparison)
    hamming_distance = sum(b1 != b2 for b1, b2 in zip(template1, template2))
    hamming_similarity = ((len(template1) - hamming_distance) / len(template1)) * 100
    
    # Method 2: Pattern Matching (look for similar byte patterns)
    pattern_matches = 0
    pattern_length = 4  # Look for 4-byte patterns
    for i in range(len(template1) - pattern_length + 1):
        pattern1 = template1[i:i+pattern_length]
        pattern2 = template2[i:i+pattern_length]
        if pattern1 == pattern2:
            pattern_matches += 1
    
    pattern_similarity = (pattern_matches / (len(template1) - pattern_length + 1)) * 100
    
    # Method 3: Feature-based comparison (byte frequency analysis)
    byte_freq1 = {}
    byte_freq2 = {}
    
    for byte in template1:
        byte_freq1[byte] = byte_freq1.get(byte, 0) + 1
    
    for byte in template2:
        byte_freq2[byte] = byte_freq2.get(byte, 0) + 1
    
    # Calculate frequency similarity
    common_bytes = set(byte_freq1.keys()) & set(byte_freq2.keys())
    freq_similarity = 0
    if byte_freq1 and byte_freq2:
        total_freq_diff = 0
        for byte in common_bytes:
            total_freq_diff += abs(byte_freq1[byte] - byte_freq2[byte])
        max_possible_diff = max(sum(byte_freq1.values()), sum(byte_freq2.values()))
        if max_possible_diff > 0:
            freq_similarity = ((max_possible_diff - total_freq_diff) / max_possible_diff) * 100
    
    # Method 4: Structural similarity (byte position importance)
    structural_matches = 0
    for i in range(0, len(template1), 8):  # Check every 8th byte (key positions)
        if i < len(template1) and i < len(template2):
            if template1[i] == template2[i]:
                structural_matches += 1
    
    structural_similarity = (structural_matches / (len(template1) // 8 + 1)) * 100
    
    # Weighted combination of all methods
    # Give more weight to hamming distance and pattern matching
    final_score = (
        hamming_similarity * 0.4 +      # 40% weight
        pattern_similarity * 0.3 +      # 30% weight
        freq_similarity * 0.2 +         # 20% weight
        structural_similarity * 0.1     # 10% weight
    )
    
    return round(final_score, 2)


def advanced_fingerprint_match(incoming_template: bytes, db_templates: list) -> tuple:
    """
    Advanced fingerprint matching with multiple validation layers.
    Returns (matched_voter, confidence_score, match_type)
    """
    if not incoming_template:
        return None, 0.0, "no_template"
    
    best_match = None
    best_score = 0.0
    match_type = "no_match"
    
    # First pass: Quick screening with lower threshold
    candidates = []
    for record in db_templates:
        try:
            db_template = bytes.fromhex(record.template_hex)
            if len(db_template) != len(incoming_template):
                continue
                
            # Quick similarity check
            quick_score = calculate_similarity(incoming_template, db_template)
            if quick_score > 15.0:  # Lower threshold for initial screening
                candidates.append((record, quick_score))
        except Exception:
            continue
    
    # Second pass: Detailed analysis of candidates
    for record, initial_score in candidates:
        try:
            db_template = bytes.fromhex(record.template_hex)
            
            # Detailed similarity calculation
            detailed_score = calculate_similarity(incoming_template, db_template)
            
            # Additional validation checks
            validation_passed = True
            
            # Check 1: Minimum byte similarity
            byte_matches = sum(b1 == b2 for b1, b2 in zip(incoming_template, db_template))
            byte_similarity = (byte_matches / len(incoming_template)) * 100
            if byte_similarity < 25.0:  # At least 25% of bytes should match
                validation_passed = False
            
            # Check 2: Pattern consistency
            pattern_consistency = 0
            for i in range(0, len(incoming_template) - 3, 4):
                if i + 4 <= len(incoming_template) and i + 4 <= len(db_template):
                    pattern1 = incoming_template[i:i+4]
                    pattern2 = db_template[i:i+4]
                    if pattern1 == pattern2:
                        pattern_consistency += 1
            
            pattern_score = (pattern_consistency / (len(incoming_template) // 4)) * 100
            if pattern_score < 10.0:  # At least 10% pattern consistency
                validation_passed = False
            
            # Check 3: Structural integrity
            structural_matches = 0
            key_positions = [0, len(incoming_template)//4, len(incoming_template)//2, 3*len(incoming_template)//4, len(incoming_template)-1]
            for pos in key_positions:
                if pos < len(incoming_template) and pos < len(db_template):
                    if incoming_template[pos] == db_template[pos]:
                        structural_matches += 1
            
            structural_score = (structural_matches / len(key_positions)) * 100
            if structural_score < 20.0:  # At least 20% of key positions should match
                validation_passed = False
            
            # Final score calculation with validation
            if validation_passed:
                final_score = (detailed_score * 0.6 + byte_similarity * 0.2 + pattern_score * 0.1 + structural_score * 0.1)
                
                if final_score > best_score:
                    best_score = final_score
                    best_match = record.voter
                    
                    # Determine match type based on score
                    if final_score >= 85.0:
                        match_type = "exact_match"
                    elif final_score >= 70.0:
                        match_type = "high_confidence"
                    elif final_score >= 55.0:
                        match_type = "medium_confidence"
                    else:
                        match_type = "low_confidence"
                        
        except Exception:
            continue
    
    return best_match, round(best_score, 2), match_type


@csrf_exempt
def match_template(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        trigger_id = data.get('trigger_id')
        template_b64 = data.get('template')

        if not trigger_id or not template_b64:
            return JsonResponse({'status': 'error', 'message': 'Missing trigger_id or template'}, status=400)

        try:
            trigger = ScanTrigger.objects.get(id=trigger_id, action='match', used=False)
        except ScanTrigger.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Trigger not found or already used'}, status=404)

        # Decode incoming base64 fingerprint template to bytes
        incoming_template = base64.b64decode(template_b64)

        # Use advanced fingerprint matching algorithm
        templates = FingerprintTemplate.objects.select_related('voter').all()
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(incoming_template, templates)

        # Strict threshold for security - only accept high confidence matches
        MINIMUM_CONFIDENCE_THRESHOLD = 55.0  # Much higher than before for security

        if matched_voter and confidence_score >= MINIMUM_CONFIDENCE_THRESHOLD:
            # Additional security check: ensure voter hasn't already voted
            if matched_voter.has_voted:
                trigger.used = True
                trigger.matched_voter = matched_voter  # Set the matched voter
                trigger.match_status = 'already_voted'
                trigger.match_message = f"Matched voter {matched_voter.name} but they have already voted"
                trigger.score = confidence_score
                trigger.save()
                
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'Voter has already voted',
                    'voter_name': matched_voter.name,
                    'score': confidence_score,
                    'match_type': match_type
                })

            # Log successful match for audit
            ActivityLog.objects.create(
                action=f'Fingerprint match successful: {matched_voter.name} (ID: {matched_voter.voter_id}) - Score: {confidence_score:.2f}, Type: {match_type}'
            )

            trigger.used = True
            trigger.matched_voter = matched_voter
            trigger.match_status = 'success'
            trigger.match_message = f"Matched voter {matched_voter.name} with score {confidence_score:.2f} ({match_type})"
            trigger.score = confidence_score
            trigger.save()

            return JsonResponse({
                'status': 'success',
                'voter_id': matched_voter.voter_id,
                'voter_name': matched_voter.name,
                'score': confidence_score,
                'match_type': match_type,
                'confidence_level': 'high' if confidence_score >= 70.0 else 'medium'
            })

        # No match found or confidence too low
        trigger.used = True
        trigger.match_status = 'not_found'
        trigger.match_message = f'No matching fingerprint found (best score: {confidence_score:.2f})'
        trigger.score = confidence_score
        trigger.save()

        # Log failed match attempt for security monitoring
        ActivityLog.objects.create(
            action=f'Fingerprint match failed - Best score: {confidence_score:.2f}, Match type: {match_type}'
        )

        return JsonResponse({
            'status': 'not_found', 
            'message': 'No matching fingerprint found with sufficient confidence', 
            'score': confidence_score,
            'match_type': match_type
        })

    except Exception as e:
        ActivityLog.objects.create(action=f'Fingerprint matching error: {str(e)}')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

@csrf_exempt
@require_http_methods(["GET"])
def get_latest_scanned_template(request):
    """Get the latest scanned fingerprint template for registration form"""
    try:
        # Get the latest template (either with or without voter)
        latest_template = FingerprintTemplate.objects.order_by('-created_at').first()
        
        if latest_template:
            return JsonResponse({
                'status': 'success',
                'template_id': latest_template.id,
                'template_hex': latest_template.template_hex,
                'created_at': latest_template.created_at.isoformat(),
                'voter_id': latest_template.voter.voter_id if latest_template.voter else None,
                'is_temporary': latest_template.voter is None
            })
        else:
            return JsonResponse({
                'status': 'no_template',
                'message': 'No fingerprint templates found'
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def fingerprint_verification(request):
    """Verify fingerprint and check if voter can vote"""
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        
        if not fingerprint_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint ID is required'
            }, status=400)
        
        # Find voter by fingerprint_id
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)
            
            # Check if voter has already voted
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Fingerprint verification attempt by already voted voter: {voter.name} (ID: {voter.voter_id})')
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'You have already voted',
                    'voter_name': voter.name,
                    'voter_id': voter.voter_id
                })
            
            # Check if there's an active voting session
            session = VotingSession.objects.filter(is_active=True).first()
            if not session:
                return JsonResponse({
                    'status': 'no_session',
                    'message': 'Voting is not currently active'
                })
            
            # Set session for authenticated voter
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            
            # Voter is verified and can vote
            ActivityLog.objects.create(action=f'Fingerprint verification successful for voter: {voter.name} (ID: {voter.voter_id})')
            return JsonResponse({
                'status': 'verified',
                'message': 'Fingerprint verified successfully',
                'voter_name': voter.name,
                'voter_id': voter.voter_id,
                'redirect_url': '/cast-vote/'
            })
            
        except Voter.DoesNotExist:
            ActivityLog.objects.create(action=f'Fingerprint verification failed - voter not found for fingerprint_id: {fingerprint_id}')
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        ActivityLog.objects.create(action=f'Fingerprint verification error: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': f'Verification error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cast_vote(request):
    """Cast vote for verified voter"""
    try:
        print(f"🔍 cast_vote called with body: {request.body}")
        data = json.loads(request.body)
        voter_id = data.get('voter_id')
        votes = data.get('votes', [])
        
        print(f"🔍 Parsed data - voter_id: {voter_id}, votes: {votes}")
        
        if not voter_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Voter ID is required'
            }, status=400)
        
        if not votes:
            return JsonResponse({
                'status': 'error',
                'message': 'No votes provided'
            }, status=400)
        
        # Find voter by voter_id
        print(f"🔍 Looking for voter with voter_id: {voter_id}")
        try:
            voter = Voter.objects.get(voter_id=voter_id)
            print(f"✅ Found voter: {voter.name} (ID: {voter.voter_id})")
            
            # Double-check if voter has already voted (race condition protection)
            if voter.has_voted:
                ActivityLog.objects.create(action=f'Vote attempt by already voted voter: {voter.name} (ID: {voter.voter_id})')
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'You have already voted',
                    'voter_name': voter.name
                })
            
            # Check if there's an active voting session
            session = VotingSession.objects.filter(is_active=True).first()
            print(f"🔍 Active voting session: {session}")
            if not session:
                print("❌ No active voting session found")
                return JsonResponse({
                    'status': 'no_session',
                    'message': 'Voting is not currently active'
                })
            
            # Process votes within a transaction
            with transaction.atomic():
                # Re-check has_voted status within transaction
                voter = Voter.objects.select_for_update().get(voter_id=voter_id)
                if voter.has_voted:
                    return JsonResponse({
                        'status': 'already_voted',
                        'message': 'You have already voted'
                    })
                
                # Record votes
                for vote_item in votes:
                    post_id = vote_item.get('post')
                    candidate_id = vote_item.get('candidate')
                    
                    if not post_id or not candidate_id:
                        continue
                    
                    try:
                        post = Post.objects.get(id=post_id)
                        candidate = Candidate.objects.get(id=candidate_id, post=post)
                        
                        # Check if voter already voted for this post
                        existing_vote = Vote.objects.filter(voter=voter, post=post).first()
                        if existing_vote:
                            continue  # Skip if already voted for this post
                        
                        Vote.objects.create(voter=voter, candidate=candidate, post=post)
                        
                    except (Post.DoesNotExist, Candidate.DoesNotExist):
                        continue
                
                # Mark voter as having voted
                voter.has_voted = True
                voter.last_vote_attempt = timezone.now()
                voter.save()
            
            ActivityLog.objects.create(action=f'Vote cast successfully by voter: {voter.name} (ID: {voter.voter_id})')
            
            return JsonResponse({
                'status': 'success',
                'message': 'Vote cast successfully',
                'voter_name': voter.name,
                'timestamp': voter.last_vote_attempt.isoformat()
            })
            
        except Voter.DoesNotExist:
            print(f"❌ Voter not found with voter_id: {voter_id}")
            ActivityLog.objects.create(action=f'Vote attempt by non-existent voter with voter_id: {voter_id}')
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print(f"❌ Exception in cast_vote: {str(e)}")
        import traceback
        traceback.print_exc()
        ActivityLog.objects.create(action=f'Vote casting error: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': f'Vote error: {str(e)}'
        }, status=500)


def vote_page(request):
    """Render the voting page for verified voters (session-based)"""
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        return redirect('voting:scanner')
    
    try:
        voter = Voter.objects.get(id=voter_id)
        if voter.has_voted:
            return redirect('/already-voted/')
        
        posts = Post.objects.prefetch_related('candidates').all()
        return render(request, 'voting/vote_page.html', {
            'voter': voter,
            'posts': posts
        })
    except Voter.DoesNotExist:
        return redirect('voting:scanner')


def vote_page_with_id(request, voter_id):
    """Render the voting page for voters with direct ID access"""
    try:
        voter = Voter.objects.get(voter_id=voter_id)
        if voter.has_voted:
            return redirect('/already-voted/')
        
        posts = Post.objects.prefetch_related('candidates').all()
        return render(request, 'voting/vote_page.html', {
            'voter': voter,
            'posts': posts
        })
    except Voter.DoesNotExist:
        return redirect('voting:scanner')


def vote_success(request):
    """Render the vote success page"""
    voter_id = request.session.get('authenticated_voter_id')
    voter = None
    
    if voter_id:
        try:
            voter = Voter.objects.get(id=voter_id)
        except Voter.DoesNotExist:
            pass
    
    return render(request, 'voting/vote_success.html', {'voter': voter})

@csrf_exempt
@staff_member_required
def get_pending_templates(request):
    """
    Return JSON list of pending fingerprint templates for dropdown,
    AND update session with the latest template ids.
    This API is called by JS to keep dropdown in sync.
    """
    # You must adjust this query to fetch the real pending templates:
    # Example: only templates without a linked voter (unassigned)
    templates = FingerprintTemplate.objects.filter(voter__isnull=True).order_by('-id')[:20]
    
    # Store the IDs in session as 'pending_template' (for your form to check)
    if templates.exists():
        # For simplicity, store list of IDs as session value
        request.session['pending_template'] = [str(t.id) for t in templates]
    else:
        request.session.pop('pending_template', None)
    
    data = [{
        'id': t.id,
        'template_hex': t.template_hex[:10] + '...'  # short preview for dropdown label
    } for t in templates]
    
    return JsonResponse(data, safe=False)

@staff_member_required
def new_voter(request):
    # Clear current voter session key to start fresh
    if 'current_voter_id' in request.session:
        del request.session['current_voter_id']
    # Also clear any pending fingerprint template session data
    request.session.pop('pending_template', None)
    request.session.pop('pending_voter_id', None)

    # Redirect back to register voter page
    return redirect('voting:register_voter')

def voter_home_with_id(request, voter_id):
    voter = get_object_or_404(Voter, voter_id=voter_id)
    return render(request, 'voting/voter_home.html', {'voter': voter})

def scan_result(request):
    trigger_id = request.GET.get('trigger_id')
    if not trigger_id:
        return JsonResponse({"status": "error", "message": "Missing trigger_id"}, status=400)
    try:
        trigger = ScanTrigger.objects.get(id=trigger_id)
    except ScanTrigger.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Trigger not found"}, status=404)

    if not trigger.used:
        # Not used yet, still pending
        return JsonResponse({"status": "pending"})

    # Check match status first
    if trigger.match_status == 'already_voted':
        # Handle already voted case
        if trigger.matched_voter:
            voter = trigger.matched_voter
            # Set session for the matched voter so already_voted page can display their name
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            
            return JsonResponse({
                "status": "already_voted",
                "voter_id": voter.voter_id,
                "voter_name": voter.name,
                "message": "This voter has already cast their vote",
                "score": trigger.score or 0
            })
        else:
            # If matched_voter is not set but status is already_voted, try to find the voter
            # This handles the case where the trigger was marked as already_voted but voter wasn't saved
            return JsonResponse({
                "status": "already_voted",
                "voter_id": None,
                "voter_name": "Unknown Voter",
                "message": "This voter has already cast their vote",
                "score": trigger.score or 0
            })
    
    elif trigger.match_status == 'success' and trigger.matched_voter:
        voter = trigger.matched_voter
        return JsonResponse({
            "status": "success",
            "voter_id": voter.voter_id,
            "voter_name": voter.name,
            "score": trigger.score or 0
        })
    
    elif trigger.match_status == 'not_found':
        return JsonResponse({
            "status": "error",
            "message": "Fingerprint not matched"
        })
    
    else:
        # Fallback for other cases
        return JsonResponse({
            "status": "error",
            "message": "Fingerprint not matched"
        })

def validate_fingerprint_template(template_hex: str) -> bool:
    """
    Validate fingerprint template format and quality.
    Returns True if template is valid and meets quality standards.
    """
    try:
        # Check if template_hex is valid hex string
        template_bytes = bytes.fromhex(template_hex)
        
        # Check minimum length (typical fingerprint templates are 512+ bytes)
        if len(template_bytes) < 256:
            return False
        
        # Check for reasonable byte distribution (not all zeros or all ones)
        zero_count = template_bytes.count(0)
        one_count = template_bytes.count(255)
        total_bytes = len(template_bytes)
        
        # If more than 80% are zeros or ones, template is likely invalid
        if zero_count / total_bytes > 0.8 or one_count / total_bytes > 0.8:
            return False
        
        # Check for reasonable entropy (not too repetitive)
        unique_bytes = len(set(template_bytes))
        if unique_bytes < total_bytes * 0.1:  # At least 10% unique bytes
            return False
        
        return True
        
    except Exception:
        return False


def calculate_template_quality(template_hex: str) -> float:
    """
    Calculate quality score for fingerprint template (0-100).
    Higher score indicates better template quality.
    """
    try:
        template_bytes = bytes.fromhex(template_hex)
        
        # Factor 1: Length (longer templates are generally better)
        length_score = min(len(template_bytes) / 512.0 * 100, 100)
        
        # Factor 2: Entropy (more unique bytes = better)
        unique_bytes = len(set(template_bytes))
        entropy_score = (unique_bytes / len(template_bytes)) * 100
        
        # Factor 3: Distribution (avoid extreme values)
        zero_count = template_bytes.count(0)
        one_count = template_bytes.count(255)
        total_bytes = len(template_bytes)
        
        distribution_score = 100
        if zero_count / total_bytes > 0.5:
            distribution_score -= 30
        if one_count / total_bytes > 0.5:
            distribution_score -= 30
        
        # Weighted average
        quality_score = (length_score * 0.3 + entropy_score * 0.4 + distribution_score * 0.3)
        
        return round(quality_score, 2)
        
    except Exception:
        return 0.0

@csrf_exempt
@require_http_methods(["POST"])
def test_fingerprint_matching(request):
    """
    Test endpoint for fingerprint matching algorithm.
    Allows testing with sample templates to verify algorithm accuracy.
    """
    try:
        data = json.loads(request.body)
        test_template_hex = data.get('template_hex')
        test_mode = data.get('mode', 'match')  # 'match' or 'quality'
        
        if not test_template_hex:
            return JsonResponse({
                'status': 'error',
                'message': 'template_hex is required for testing'
            }, status=400)
        
        # Validate template
        if not validate_fingerprint_template(test_template_hex):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid template format for testing'
            }, status=400)
        
        quality_score = calculate_template_quality(test_template_hex)
        
        if test_mode == 'quality':
            return JsonResponse({
                'status': 'success',
                'quality_score': quality_score,
                'is_valid': True,
                'message': f'Template quality: {quality_score:.1f}/100'
            })
        
        # Test matching against all stored templates
        test_template = bytes.fromhex(test_template_hex)
        templates = FingerprintTemplate.objects.select_related('voter').all()
        
        matched_voter, confidence_score, match_type = advanced_fingerprint_match(test_template, templates)
        
        results = {
            'status': 'success',
            'test_template_quality': quality_score,
            'total_templates_tested': len(templates),
            'best_match_score': confidence_score,
            'match_type': match_type,
            'threshold_met': confidence_score >= 55.0
        }
        
        if matched_voter:
            results.update({
                'matched_voter_id': matched_voter.voter_id,
                'matched_voter_name': matched_voter.name,
                'voter_has_voted': matched_voter.has_voted
            })
        
        return JsonResponse(results)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Test failed: {str(e)}'
        }, status=500)
