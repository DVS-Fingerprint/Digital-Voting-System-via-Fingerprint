from django.shortcuts import render, get_object_or_404, redirect
from .models import Candidate, Voter, Vote, Post, VotingSession
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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
from .models import FingerprintTemplate, ActivityLog
import base64
from django.db import transaction
from django.views.decorators.csrf import csrf_protect


@staff_member_required
def register_voter(request):
    success = False
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            voter = form.save()
            template_hex = form.cleaned_data.get('template_hex')
            if template_hex:
                FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
            success = True
            form = VoterRegistrationForm()  # Reset form after success
    else:
        form = VoterRegistrationForm()
    return render(request, 'voting/register_voter.html', {'form': form, 'success': success})

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

@api_view(['POST'])
def authenticate_fingerprint(request):
    """ESP32 sends fingerprint_id, returns voter status."""
    fingerprint_id = request.data.get('fingerprint_id')
    try:
        voter = Voter.objects.get(fingerprint_id=fingerprint_id)  # type: ignore
        if voter.has_voted:
            return Response({'status': 'already_voted', 'name': voter.name}, status=200)
        return Response({'status': 'ok', 'name': voter.name}, status=200)
    except Voter.DoesNotExist:  # type: ignore
        return Response({'status': 'not_found'}, status=404)

# Simplified fingerprint API endpoints

@csrf_exempt  # Required for ESP32 hardware POSTs (no CSRF token support)
@require_http_methods(["POST"])
def fingerprint_scan(request):
    """Receive fingerprint ID from ESP32 - simplified version"""
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        
        # Just acknowledge receipt - no storage needed
        return JsonResponse({
            'status': 'success',
            'message': 'Fingerprint scan received',
            'fingerprint_id': fingerprint_id
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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

@csrf_exempt  # Required for ESP32 hardware GETs (no CSRF token support)
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

@require_http_methods(["POST"])
def verify_fingerprint(request):
    """Verify fingerprint ID and return voter status with redirect URL"""
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        
        if not fingerprint_id:
            return JsonResponse({'error': 'fingerprint_id is required'}, status=400)
        
        try:
            voter = Voter.objects.get(fingerprint_id=fingerprint_id)  # type: ignore
            
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
                    'redirect_url': '/voting/vote/'  # URL to voting interface
                })
                
        except Voter.DoesNotExist:  # type: ignore
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

def dashboard(request):
    # This view is being deprecated in favor of the new flow.
    # It will be removed once the transition is complete.
    from .models import Post
    posts = Post.objects.prefetch_related('candidates').all()  # type: ignore
    session_countdown = 300
    return render(request, 'voting/election.html', {'posts': posts, 'session_countdown': session_countdown})

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

def upload_template(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            template_b64 = data.get('template_hex')

            print("\U0001F4E5 Received template for user_id:", user_id)
            print("\U0001F9EC Template (first 100 chars):", template_b64[:100])

            # Decode base64 string to bytes
            template_bytes = base64.b64decode(template_b64)

            # Convert bytes back to hex string if you want to store as hex text
            template_hex = template_bytes.hex()

            FingerprintTemplate.objects.create(
                user_id=user_id,
                template_hex=template_hex
            )

            return JsonResponse({'status': 'success'})
        except Exception as e:
            print("\u274C Error:", str(e))
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
