from django.urls import path, include
from . import views

app_name = 'voting'

urlpatterns = [
    # BioMatdaan User Flow
    path('', views.home, name='home'),
    path('scanner/', views.scanner, name='scanner'),
    path('voter-home/', views.voter_home, name='voter_home'),
    path('vote/', views.election_view, name='election_view'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('thank-you/', views.thankyou, name='thankyou'),

    # Admin/Staff Views
    path('register-voter/', views.register_voter, name='register_voter'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # API Endpoints
    path('api/', include([
        path('posts/', views.posts_list, name='posts_list'),
        path('candidates/', views.candidates_list, name='candidates_list'),
        path('vote/', views.vote_view, name='vote'),
        path('results/', views.results_view, name='results'),
        path('register-candidate/', views.register_candidate, name='register_candidate'),
        path('dashboard-data/', views.dashboard_view, name='dashboard_data'),
        path('authenticate-fingerprint/', views.authenticate_fingerprint, name='authenticate_fingerprint'),
    ])),
]
