from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_GET
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

import base64, json

from .models import (
    Voter, Candidate, Vote, Post, VotingSession, FingerprintTemplate, ActivityLog, ScanTrigger
)
from .forms import VoterRegistrationForm
from .serializers import VoterSerializer, PostSerializer, CandidateSerializer, VoteSerializer, VotingSessionSerializer
from .matcher import match_templates
from django.utils import timezone

@staff_member_required
def register_voter(request):
    success = False
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            success = True
            form = VoterRegistrationForm()
    else:
        form = VoterRegistrationForm()
    return render(request, 'voting/register_voter.html', {'form': form, 'success': success})


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
    fingerprint_id = request.data.get('fingerprint_id')
    votes = request.data.get('votes')
    try:
        voter = Voter.objects.get(fingerprint_id=fingerprint_id)
        if voter.has_voted:
            return Response({'detail': 'Already voted.'}, status=400)
        session = VotingSession.objects.filter(is_active=True).first()
        if not session:
            return Response({'detail': 'Voting is not active.'}, status=403)
        for vote_item in votes:
            post = Post.objects.get(id=vote_item['post'])
            candidate = Candidate.objects.get(id=vote_item['candidate'], post=post)
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
    fingerprint_id = request.data.get('fingerprint_id')
    try:
        voter = Voter.objects.get(fingerprint_id=fingerprint_id)
        if voter.has_voted:
            return Response({'status': 'already_voted', 'name': voter.name}, status=200)
        return Response({'status': 'ok', 'name': voter.name}, status=200)
    except Voter.DoesNotExist:
        return Response({'status': 'not_found'}, status=404)


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
    return JsonResponse({
        'status': 'no_scan',
        'fingerprint_id': None,
        'message': 'Fingerprint scanning simplified - enter ID manually'
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
                return JsonResponse({
                    'status': 'already_voted',
                    'message': 'You have already voted',
                    'voter_name': voter.name
                })
            request.session['authenticated_voter_id'] = voter.id
            request.session.modified = True
            return JsonResponse({
                'status': 'authenticated',
                'message': 'Voter authenticated successfully',
                'voter_name': voter.name,
                'redirect_url': '/voting/vote/'
            })
        except Voter.DoesNotExist:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Voter not found with this fingerprint ID'
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def submit_vote(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        data = json.loads(request.body)
        votes = data.get('votes', [])
        if not votes:
            return JsonResponse({'error': 'No votes provided'}, status=400)
        session = VotingSession.objects.filter(is_active=True).first()
        if not session:
            return JsonResponse({'error': 'Voting is not active'}, status=403)
        for vote_item in votes:
            post_id = vote_item.get('post')
            candidate_id = vote_item.get('candidate')
            if not post_id or not candidate_id:
                continue
            try:
                post = Post.objects.get(id=post_id)
                candidate = Candidate.objects.get(id=candidate_id, post=post)
                Vote.objects.create(candidate=candidate, post=post)
            except (Post.DoesNotExist, Candidate.DoesNotExist):
                continue
        request.session.pop('authenticated_voter_id', None)
        return JsonResponse({
            'status': 'success',
            'message': 'Vote submitted successfully',
            'voter_name': None
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def logout_voter(request):
    request.session.pop('authenticated_voter_id', None)
    return redirect('voting:home')



@csrf_exempt
@require_http_methods(["POST"])
def trigger_scan(request):
    try:
        data = json.loads(request.body)
        voter_id = data.get("voter_id")
        action = data.get("action")

        if action not in ["register", "match"]:
            return JsonResponse({"error": "Invalid action"}, status=400)

        if action == "register" and not voter_id:
            return JsonResponse({"error": "voter_id required for registration"}, status=400)

        ScanTrigger.objects.all().delete()
        ScanTrigger.objects.create(voter_id=voter_id if voter_id else None, action=action)
        ActivityLog.objects.create(action=f"Scan trigger created for voter ID {voter_id} ({action})")

        return JsonResponse({"message": "Scan trigger created"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_scan_trigger(request):
    latest_trigger = ScanTrigger.objects.order_by("-created_at").first()
    if latest_trigger:
        response = {
            "voter_id": latest_trigger.voter_id,
            "action": latest_trigger.action
        }
        latest_trigger.delete()
        return JsonResponse(response)
    return JsonResponse({"action": None, "voter_id": None})


@csrf_exempt
@require_http_methods(["POST"])
def upload_template(request):
    try:
        data = json.loads(request.body)
        voter_id = data.get('voter_id')
        template_b64 = data.get('template_hex')

        if not voter_id or not template_b64:
            return JsonResponse({'status': 'error', 'message': 'Missing voter_id or template_hex'}, status=400)

        try:
            template_bytes = base64.b64decode(template_b64)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Invalid base64 template'}, status=400)

        template_hex = template_bytes.hex()
        voter = Voter.objects.get(id=voter_id)

        FingerprintTemplate.objects.create(voter=voter, template_hex=template_hex)
        return JsonResponse({'status': 'success'})
    except Voter.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Voter not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def match_template(request):
    try:
        data = json.loads(request.body)
        template_b64 = data.get('template')

        if not template_b64:
            return JsonResponse({'status': 'error', 'message': 'No template provided'}, status=400)

        incoming_template = base64.b64decode(template_b64)
        all_templates = FingerprintTemplate.objects.select_related('voter').all()

        for record in all_templates:
            db_template_bytes = bytes.fromhex(record.template_hex)
            match_score = match_templates(incoming_template, db_template_bytes)

            if match_score > 20:
                voter = record.voter
                if not voter:
                    continue

                if voter.has_voted:
                    return JsonResponse({'status': 'already_voted', 'voter_name': voter.name})

                voter.has_voted = True
                voter.last_vote_attempt = now()
                voter.save()

                return JsonResponse({
                    'status': 'authenticated',
                    'voter_name': voter.name,
                    'redirect_url': '/voting/vote/'
                })

        return JsonResponse({'status': 'not_found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
