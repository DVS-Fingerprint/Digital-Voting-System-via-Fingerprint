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
            selected_template_id = form.cleaned_data.get('template_hex')
            if selected_template_id:
                try:
                    selected_template = FingerprintTemplate.objects.get(id=selected_template_id)
                    # Remove old templates for this voter
                    FingerprintTemplate.objects.filter(voter=voter).delete()

                    # Link or create template
                    if selected_template.voter is None:
                        selected_template.voter = voter
                        selected_template.save()
                    else:
                        FingerprintTemplate.objects.create(voter=voter, template_hex=selected_template.template_hex)

                    # Clear pending template from session
                    request.session.pop('pending_template', None)
                    request.session.pop('pending_voter_id', None)
                except FingerprintTemplate.DoesNotExist:
                    pass
            success = True
    else:
        # On GET, pre-fill form with current voter data and template if exists
        initial_data = {}
        pending_template = request.session.get('pending_template')
        if pending_template:
            initial_data['template_hex'] = pending_template

        form = VoterRegistrationForm(instance=voter, initial=initial_data)

    context = {
        'form': form,
        'success': success,
        'next_voter_id': current_voter_id,
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

<<<<<<< HEAD

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


=======
>>>>>>> origin/feature/smriti
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

        if voter_id:
            try:
                print(f"🔍 Looking for voter_id: {voter_id}")
                voter = Voter.objects.get(voter_id__iexact=voter_id)
                FingerprintTemplate.objects.filter(voter=voter).delete()
                FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
                print(f"✅ Created FingerprintTemplate for voter {voter_id}")

                trigger = ScanTrigger.objects.filter(voter_id=voter_id, used=False).order_by('-created_at').first()
                if trigger:
                    trigger.used = True
                    trigger.save()
                    print(f"✅ Marked trigger as used for voter_id={voter_id}")

                return JsonResponse({'status': 'success'})
            except Voter.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Voter not found'}, status=400)
        else:
            temp_template = FingerprintTemplate.objects.create(
                voter=None,
                template_hex=template_hex
            )
            print(f"🗃️ Created temporary FingerprintTemplate with id {temp_template.id}")
            return JsonResponse({
                'status': 'success',
                'template_id': temp_template.id,
                'message': 'Template stored successfully'
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


def calculate_similarity(template1: bytes, template2: bytes) -> float:
    """
    Returns similarity between two fingerprint templates (0 to 100).
    Simple normalized Hamming distance approximation.
    """
    if not template1 or not template2 or len(template1) != len(template2):
        return 0.0

    match_count = sum(b1 == b2 for b1, b2 in zip(template1, template2))
    return (match_count / len(template1)) * 100



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

        best_score = 0
        matched_voter = None

        templates = FingerprintTemplate.objects.select_related('voter').all()
        for record in templates:
            try:
                db_template = bytes.fromhex(record.template_hex)
            except Exception:
                continue  # Skip corrupted templates

            score = calculate_similarity(incoming_template, db_template)
            if score > best_score:
                best_score = score
                matched_voter = record.voter

        SIMILARITY_THRESHOLD = 20.0  # Adjust threshold for match sensitivity

        if matched_voter and best_score >= SIMILARITY_THRESHOLD:
            # Optionally, check if voter has voted already here if needed

            trigger.used = True
            trigger.matched_voter = matched_voter
            trigger.match_status = 'success'
            trigger.match_message = f"Matched voter {matched_voter.name} with score {best_score:.2f}"
            trigger.save()

            return JsonResponse({
                'status': 'success',
                'voter_id': matched_voter.voter_id,
                'voter_name': matched_voter.name,
                'score': best_score
            })

        # No match found
        trigger.used = True
        trigger.match_status = 'not_found'
        trigger.match_message = 'No matching fingerprint found'
        trigger.save()

        return JsonResponse({'status': 'not_found', 'message': 'No matching fingerprint found', 'score': best_score})

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

<<<<<<< HEAD

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
=======
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

def voter_home(request, voter_id):
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

    # Find matched voter
    if trigger.matched_voter:
        voter = trigger.matched_voter
        return JsonResponse({
            "status": "success",
            "voter_id": voter.voter_id,
            "voter_name": voter.name,
            "score": trigger.score or 0
        })
    else:
        return JsonResponse({
            "status": "error",
            "message": "Fingerprint not matched"
        })
>>>>>>> origin/feature/smriti
