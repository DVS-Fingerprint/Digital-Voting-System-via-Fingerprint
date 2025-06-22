from django.shortcuts import render, get_object_or_404, redirect
from .models import Candidate, Voter, Vote, Post, VotingSession
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .forms import VoterRegistrationForm
from rest_framework import status, permissions, generics, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.contrib.auth.decorators import login_required
from .serializers import (
    VoterSerializer, PostSerializer, CandidateSerializer, VoteSerializer,
    VotingSessionSerializer
)
from rest_framework.permissions import IsAdminUser

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
    total_voters = Voter.objects.count()
    total_candidates = Candidate.objects.count()
    total_votes = Vote.objects.count()
    # Vote counts by candidate
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
    return render(request, 'voting/voter_home.html')

def candidate_list(request):
    posts = Post.objects.all()
    return render(request, 'voting/candidate_list.html', {'posts': posts})

@api_view(['GET'])
def posts_list(request):
    posts = Post.objects.all()
    serializer = PostSerializer(posts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def candidates_list(request):
    post_id = request.GET.get('post_id')
    candidates = Candidate.objects.all()
    if post_id:
        candidates = candidates.filter(post_id=post_id)
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def vote_view(request):
    """Accepts UID and selected candidate IDs, stores vote."""
    uid = request.data.get('uid')
    votes = request.data.get('votes')  # [{post: id, candidate: id}]
    try:
        voter = Voter.objects.get(uid=uid)
        if voter.has_voted:
            return Response({'detail': 'Already voted.'}, status=400)
        # Check voting session
        session = VotingSession.objects.filter(is_active=True).first()
        if not session:
            return Response({'detail': 'Voting is not active.'}, status=403)
        for vote_item in votes:
            post_id = vote_item['post']
            candidate_id = vote_item['candidate']
            post = Post.objects.get(id=post_id)
            candidate = Candidate.objects.get(id=candidate_id, post=post)
            Vote.objects.create(voter=voter, candidate=candidate, post=post)
        voter.has_voted = True
        voter.last_vote_attempt = timezone.now()
        voter.save()
        return Response({'detail': 'Vote cast successfully.', 'name': voter.name, 'timestamp': voter.last_vote_attempt})
    except Voter.DoesNotExist:
        return Response({'detail': 'Voter not found.'}, status=404)
    except Exception as e:
        return Response({'detail': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def results_view(request):
    posts = Post.objects.all()
    results = []
    for post in posts:
        candidates = Candidate.objects.filter(post=post)
        candidate_results = []
        for candidate in candidates:
            votes = Vote.objects.filter(candidate=candidate).count()
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
    """ESP32 sends UID, returns voter status."""
    uid = request.data.get('uid')
    try:
        voter = Voter.objects.get(uid=uid)
        if voter.has_voted:
            return Response({'status': 'already_voted', 'name': voter.name}, status=200)
        return Response({'status': 'ok', 'name': voter.name}, status=200)
    except Voter.DoesNotExist:
        return Response({'status': 'not_found'}, status=404)

def scanner(request):
    return render(request, 'voting/scanner.html')

def election_view(request):
    posts = Post.objects.prefetch_related('candidates').all()
    if request.method == 'POST':
        # Logic to handle vote submission will go here
        return redirect('voting:thankyou')
    return render(request, 'voting/election.html', {'posts': posts})

def thankyou(request):
    # Example: show choices summary (replace with real logic)
    choices = request.session.get('choices', [])
    return render(request, 'voting/confirmation.html', {'choices': choices})

def dashboard(request):
    # This view is being deprecated in favor of the new flow.
    # It will be removed once the transition is complete.
    from .models import Post
    posts = Post.objects.prefetch_related('candidates').all()
    session_countdown = 300
    return render(request, 'voting/election.html', {'posts': posts, 'session_countdown': session_countdown})