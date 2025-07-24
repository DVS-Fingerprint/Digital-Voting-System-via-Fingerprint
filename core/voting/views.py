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
    VotingSessionSerializer
)
from rest_framework.permissions import IsAdminUser
import json
from functools import wraps

# Custom decorator to check if voter is authenticated via fingerprint
def fingerprint_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        voter_id = request.session.get('authenticated_voter_id')
        if not voter_id:
            return redirect('voting:scanner')
        
        try:
            voter = Voter.objects.get(id=voter_id, fingerprint_id__isnull=False)  # type: ignore
            if voter.has_voted:
                return redirect('voting:already_voted')
            request.voter = voter
            return view_func(request, *args, **kwargs)
        except Voter.DoesNotExist:  # type: ignore
            # Clear invalid session
            request.session.pop('authenticated_voter_id', None)
            return redirect('voting:scanner')
    return _wrapped_view

# Remove or update old views that used Election
# def home(request):
#     elections = Election.objects.filter(is_active=True)
#     return render(request, 'voting/home.html', {'elections': elections})

# def election(request, election_id):
#     election = get_object_or_404(Election, id=election_id)
#     candidates = Candidate.objects.filter(election=election)
#     return render(request, 'voting/election.html', {'election': election, 'candidates': candidates})

# def vote(request, candidate_id):
#     # Simulate voter identification (replace with fingerprint auth later)
#     voter = Voter.objects.first()  # Just picking first voter for now - to be updated
#     candidate = get_object_or_404(Candidate, id=candidate_id)
#     # Check if voter has already voted
#     if voter.has_voted:
#         return HttpResponse("You have already voted!")
#     # Create vote
#     Vote.objects.create(voter=voter, candidate=candidate)
#     voter.has_voted = True
#     voter.save()
#     return HttpResponse(f"Thanks for voting for {candidate.name}!")

# def live_results(request):
#     candidates = Candidate.objects.all()
#     return render(request, 'results.html', {'candidates': candidates})

@staff_member_required
def register_voter(request):
    success = False
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
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
    voter_id = request.session.get('authenticated_voter_id')
    if not voter_id:
        return redirect('voting:scanner')
    try:
        voter = Voter.objects.get(id=voter_id)  # type: ignore
        if voter.has_voted:
            return redirect('voting:already_voted')
        return render(request, 'voting/voter_home.html', {'voter': voter})
    except Voter.DoesNotExist:  # type: ignore
        request.session.pop('authenticated_voter_id', None)
        return redirect('voting:scanner')

def candidate_list(request):
    posts = Post.objects.all()  # type: ignore
    return render(request, 'voting/candidate_list.html', {'posts': posts})

@api_view(['GET'])
def posts_list(request):
    posts = Post.objects.all()  # type: ignore
    serializer = PostSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def candidates_list(request):
    post_id = request.GET.get('post_id')
    candidates = Candidate.objects.all()  # type: ignore
    if post_id:
        candidates = candidates.filter(post_id=post_id)
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def vote_view(request):
    """Accepts fingerprint_id and selected candidate IDs, stores vote."""
    fingerprint_id = request.data.get('fingerprint_id')
    votes = request.data.get('votes')  # [{post: id, candidate: id}]
    try:
        voter = Voter.objects.get(fingerprint_id=fingerprint_id)  # type: ignore
        if voter.has_voted:
            return Response({'detail': 'Already voted.'}, status=400)
        # Check voting session
        session = VotingSession.objects.filter(is_active=True).first()  # type: ignore
        if not session:
            return Response({'detail': 'Voting is not active.'}, status=403)
        for vote_item in votes:
            post_id = vote_item['post']
            candidate_id = vote_item['candidate']
            post = Post.objects.get(id=post_id)  # type: ignore
            candidate = Candidate.objects.get(id=candidate_id, post=post)  # type: ignore
            Vote.objects.create(voter=voter, candidate=candidate, post=post)  # type: ignore
        voter.has_voted = True
        voter.last_vote_attempt = timezone.now()
        voter.save()
        return Response({'detail': 'Vote cast successfully.', 'name': voter.name, 'timestamp': voter.last_vote_attempt})
    except Voter.DoesNotExist:  # type: ignore
        return Response({'detail': 'Voter not found.'}, status=404)
    except Exception as e:
        return Response({'detail': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def results_view(request):
    posts = Post.objects.all()  # type: ignore
    results = []
    for post in posts:
        candidates = Candidate.objects.filter(post=post)  # type: ignore
        candidate_results = []
        for candidate in candidates:
            votes = Vote.objects.filter(candidate=candidate).count()  # type: ignore
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

@csrf_exempt
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

@csrf_exempt
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

@csrf_exempt
@require_http_methods(["GET"])
def get_latest_fingerprint(request):
    """Get the most recent fingerprint scan for admin form auto-fill"""
    # For simplicity, return a placeholder - in real implementation,
    # you might want to store this temporarily or use a different approach
    return JsonResponse({
        'status': 'no_scan',
        'fingerprint_id': None,
        'message': 'Fingerprint scanning simplified - enter ID manually'
    })

@csrf_exempt
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
    return render(request, 'voting/scanner.html')

@fingerprint_required
def election_view(request):
    posts = Post.objects.prefetch_related('candidates').all()  # type: ignore
    if request.method == 'POST':
        # Logic to handle vote submission will go here
        return redirect('voting:thankyou')
    return render(request, 'voting/election.html', {'posts': posts, 'voter': request.voter})

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

@csrf_exempt
@require_http_methods(["POST"])
def authenticate_voter(request):
    """Authenticate voter via fingerprint and create session"""
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
                    'message': 'You have already voted',
                    'voter_name': voter.name
                })
            
            # Create session for authenticated voter
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            
            return JsonResponse({
                'status': 'authenticated',
                'message': 'Voter authenticated successfully',
                'voter_name': voter.name,
                'redirect_url': '/voting/vote/'
            })
                
        except Voter.DoesNotExist:  # type: ignore
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint ID'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@fingerprint_required
def submit_vote(request):
    """Submit vote with authentication check"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        votes = data.get('votes', [])
        
        if not votes:
            return JsonResponse({'error': 'No votes provided'}, status=400)
        
        # Check voting session
        session = VotingSession.objects.filter(is_active=True).first()  # type: ignore
        if not session:
            return JsonResponse({'error': 'Voting is not active'}, status=403)
        
        # Record votes (simulate, no voter check)
        for vote_item in votes:
            post_id = vote_item.get('post')
            candidate_id = vote_item.get('candidate')
            
            if not post_id or not candidate_id:
                continue
                
            try:
                post = Post.objects.get(id=post_id)  # type: ignore
                candidate = Candidate.objects.get(id=candidate_id, post=post)  # type: ignore
                Vote.objects.create(voter=request.voter, candidate=candidate, post=post)  # type: ignore
            except (Post.DoesNotExist, Candidate.DoesNotExist):  # type: ignore
                continue
        
        # Mark voter as voted
        # request.voter.has_voted = True # This line is removed as voter is not authenticated
        # request.voter.last_vote_attempt = timezone.now() # This line is removed as voter is not authenticated
        # request.voter.save() # This line is removed as voter is not authenticated
        
        # Clear session
        request.session.pop('authenticated_voter_id', None)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Vote submitted successfully',
            'voter_name': request.voter.name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def logout_voter(request):
    """Logout voter and clear session"""
    request.session.pop('authenticated_voter_id', None)
    return redirect('voting:home')