from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    path('', views.home, name='home'),                    # Homepage - list elections or welcome page
    path('election/<int:election_id>/', views.election, name='election'),   # Show candidates & vote
    path('vote/<int:candidate_id>/', views.vote, name='vote'),  # Vote for candidate
    path('results/', views.live_results, name='results'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
