from django.shortcuts import render, get_object_or_404, redirect
from .models import Election, Candidate, Voter, Vote
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

def home(request):
    elections = Election.objects.filter(is_active=True)
    return render(request, 'voting/home.html', {'elections': elections})

def election(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    candidates = Candidate.objects.filter(election=election)
    return render(request, 'voting/election.html', {'election': election, 'candidates': candidates})

def vote(request, candidate_id):
    # Simulate voter identification (replace with fingerprint auth later)
    voter = Voter.objects.first()  # Just picking first voter for now - to be updated

    candidate = get_object_or_404(Candidate, id=candidate_id)

    # Check if voter has already voted
    if voter.has_voted:
        return HttpResponse("You have already voted!")

    # Create vote
    Vote.objects.create(voter=voter, candidate=candidate)
    voter.has_voted = True
    voter.save()

    return HttpResponse(f"Thanks for voting for {candidate.name}!")

def live_results(request):
    candidates = Candidate.objects.all()
    return render(request, 'results.html', {'candidates': candidates})

@staff_member_required
def admin_dashboard(request):
    context = {
        'total_voters': Voter.objects.count(),
        'total_candidates': Candidate.objects.count(),
        'total_votes': Vote.objects.count(),
        'candidates': Candidate.objects.all(),
    }
    return render(request, 'dashboard.html', context)