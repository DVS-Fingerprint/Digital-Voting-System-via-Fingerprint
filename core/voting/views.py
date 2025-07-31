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
            selected_template = form.cleaned_data.get('template_hex')
            if selected_template:
                # Check if fingerprint template already exists for this voter
                FingerprintTemplate.objects.filter(voter=voter).delete()  # Remove old template
                
                # If the selected template is temporary (no voter), link it to this voter
                if selected_template.voter is None:
                    selected_template.voter = voter
                    selected_template.save()
                else:
                    # Create a new template for this voter
                    FingerprintTemplate.objects.create(voter=voter, template_hex=selected_template.template_hex)
                
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
                return redirect('voting:already_voted')
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
    """ESP32 sends fingerprint template, returns voter status using similarity matching."""
    try:
        template_hex = request.data.get('template_hex')
        if not template_hex:
            return Response({'error': 'template_hex is required'}, status=400)
        
        # Use similarity-based matching
        # match_result = fingerprint_matcher.find_best_match(template_hex)
        
        # For now, return a simple response
        return Response({'status': 'not_found'}, status=404)
          
    except Exception as e:
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
                    'redirect_url': '/voting/vote/'
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
                'redirect_url': '/voting/vote/'
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

        if action == "register" and not voter_id:
            print(f"❌ Missing voter_id for register action")
            return JsonResponse({"error": "voter_id required for registration"}, status=400)

        # Create a scan trigger for ESP32 to poll
        # Clear any existing triggers first
        print(f"🔍 Clearing existing triggers...")
        ScanTrigger.objects.all().delete()
        
        # Create new trigger
        print(f"🔍 Creating new trigger with voter_id={voter_id}, action={action}")
        trigger = ScanTrigger.objects.create(
            voter_id=voter_id if voter_id else None,
            action=action,
            is_used=False
        )

        # Log the scan trigger action
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
        trigger = ScanTrigger.objects.filter(is_used=False).order_by('-created_at').first()
        
        if trigger:
            print(f"✅ Found trigger: voter_id={trigger.voter_id}, action={trigger.action}, id={trigger.id}")
            # Mark as used
            trigger.is_used = True
            trigger.save()
            print(f"✅ Trigger marked as used")
            
            return JsonResponse({
                "action": trigger.action,
                "voter_id": trigger.voter_id
            })
        else:
            print(f"❌ No unused triggers found")
            # Check if there are any triggers at all
            all_triggers = ScanTrigger.objects.all().order_by('-created_at')[:5]
            print(f"🔍 Recent triggers: {[f'ID:{t.id}, voter_id:{t.voter_id}, action:{t.action}, used:{t.is_used}' for t in all_triggers]}")
            
            return JsonResponse({"action": None, "voter_id": None})
    except Exception as e:
        print(f"❌ Error in get_scan_trigger: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def upload_template(request):
    """Upload fingerprint template for registration"""
    try:
        if request.method == "GET":
            # For testing purposes, return a simple response
            return JsonResponse({
                'status': 'info',
                'message': 'This endpoint accepts POST requests with template_hex and voter_id',
                'example': {
                    'template_hex': 'your_template_hex_data',
                    'voter_id': 'optional_voter_id'
                }
            })
        
        # Handle POST request
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        voter_id = data.get('voter_id')
        
        if not template_hex:
            return JsonResponse({'status': 'error', 'message': 'No template provided'}, status=400)
        
        if voter_id:
            try:
                voter = Voter.objects.get(voter_id=voter_id)
                # Remove any existing template for this voter
                FingerprintTemplate.objects.filter(voter=voter).delete()
                # Create new template
                FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
                return JsonResponse({'status': 'success'})
            except Voter.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Voter not found'}, status=400)
        else:
            # Store template without voter (for registration workflow)
            # Create a temporary template that will be linked to voter during registration
            temp_template = FingerprintTemplate.objects.create(
                voter=None,  # Will be updated during registration
                template_hex=template_hex
            )
            return JsonResponse({
                'status': 'success',
                'template_id': temp_template.id,
                'message': 'Template stored successfully'
            })
    except Exception as e:
        print("❌ Error:", str(e))
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)


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
    """Authenticate a voter by fingerprint template (exact match)."""
    try:
        data = json.loads(request.body)
        template_hex = data.get('template_hex')
        if not template_hex:
            return JsonResponse({'error': 'Missing template_hex.'}, status=400)
        try:
            fp = FingerprintTemplate.objects.select_related('voter').get(template_hex=template_hex)
            voter = fp.voter
            if voter.has_voted:
                return JsonResponse({'status': 'already_voted', 'voter_name': voter.name})
            # Set session for authenticated voter
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            return JsonResponse({'status': 'authenticated', 'voter_id': voter.id, 'voter_name': voter.name})
        except FingerprintTemplate.DoesNotExist:
            return JsonResponse({'error': 'Fingerprint not recognized.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def match_template(request):
    """Match fingerprint template for authentication"""
    try:
        data = json.loads(request.body)
        template_b64 = data.get('template')
        
        if not template_b64:
            return JsonResponse({'status': 'error', 'message': 'No template provided'}, status=400)

        incoming_template = base64.b64decode(template_b64)
        all_templates = FingerprintTemplate.objects.select_related('voter').all()

        for record in all_templates:
            db_template_bytes = bytes.fromhex(record.template_hex)
            # match_score = match_templates(incoming_template, db_template_bytes)
            match_score = 0  # Placeholder for now

            if match_score > 20:
                voter = record.voter
                if not voter:
                    continue

                if voter.has_voted:
                    return JsonResponse({'status': 'already_voted', 'voter_name': voter.name})

                voter.has_voted = True
                voter.last_vote_attempt = now()
                voter.save()

                return JsonResponse({'status': 'success', 'voter_name': voter.name})

        return JsonResponse({'status': 'not_found', 'message': 'No matching fingerprint found'})

    except Exception as e:
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
                'redirect_url': '/voting/cast-vote/'
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
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        votes = data.get('votes', [])
        
        if not fingerprint_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint ID is required'
            }, status=400)
        
        if not votes:
            return JsonResponse({
                'status': 'error',
                'message': 'No votes provided'
            }, status=400)
        
        # Find voter by fingerprint_id
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)
            
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
            if not session:
                return JsonResponse({
                    'status': 'no_session',
                    'message': 'Voting is not currently active'
                })
            
            # Process votes within a transaction
            with transaction.atomic():
                # Re-check has_voted status within transaction
                voter = Voter.objects.select_for_update().get(fingerprint_id=fingerprint_id)
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
            ActivityLog.objects.create(action=f'Vote attempt by non-existent voter with fingerprint_id: {fingerprint_id}')
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
        ActivityLog.objects.create(action=f'Vote casting error: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': f'Vote error: {str(e)}'
        }, status=500)


def vote_page(request):
    """Render the voting page for verified voters"""
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        return redirect('voting:scanner')
    
    try:
        voter = Voter.objects.get(id=voter_id)
        if voter.has_voted:
            return redirect('voting:already_voted')
        
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
