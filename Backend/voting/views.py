from django.shortcuts import render, get_object_or_404, redirect
from .models import Election, Candidate, Voter, Vote
from django.utils import timezone
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from .forms import VoterRegistrationForm
from django.shortcuts import render, redirect

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

def register_voter(request):
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard')  # or a confirmation page
    else:
        form = VoterRegistrationForm()
    return render(request, 'voting/register_voter.html', {'form': form})
   
@staff_member_required
def admin_dashboard(request):
    total_voters = Voter.objects.count()
    total_candidates = Candidate.objects.count()
    total_votes = Vote.objects.count()

    # Optional: simulate live voting activity
    live_voting_activity = Vote.objects.order_by('-timestamp')[:15].count()

    # Vote counts by candidate
    vote_counts = Candidate.objects.annotate(num_votes=Count('vote')).order_by('-num_votes')

    context = {
        'total_voters': total_voters,
        'total_candidates': total_candidates,
        'total_votes': total_votes,
        'live_voting_activity': live_voting_activity,
        'vote_counts': vote_counts,
    }

    return render(request, 'voting/admin_dashboard.html', context)