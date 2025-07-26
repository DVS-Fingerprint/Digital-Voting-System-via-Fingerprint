from django.urls import path, include
from . import views
from .views import upload_template, register_voter_with_fingerprint, fingerprint_authenticate

app_name = 'voting'

urlpatterns = [
    # BioMatdaan User Flow
    path('', views.home, name='home'),
    path('scanner/', views.scanner, name='scanner'),
    path('voter-home/', views.voter_home, name='voter_home'),
    path('vote/', views.election_view, name='election_view'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('thank-you/', views.thankyou, name='thankyou'),
    path('already-voted/', views.already_voted, name='already_voted'),
    path('logout/', views.logout_voter, name='logout_voter'),

    # Admin/Staff Views
    path('register-voter/', views.register_voter, name='register_voter'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ✅ Place this outside the API include
    path("api/upload-template/", views.upload_template, name="upload_template"),
    
    # API Endpoints
    path('api/', include([
        path('posts/', views.posts_list, name='posts_list'),
        path('candidates/', views.candidates_list, name='candidates_list'),
        path('vote/', views.vote_view, name='vote'),
        path('results/', views.results_view, name='results'),
        path('register-candidate/', views.register_candidate, name='register_candidate'),
        path('dashboard-data/', views.dashboard_view, name='dashboard_data'),
        path('authenticate-fingerprint/', views.authenticate_fingerprint, name='authenticate_fingerprint'),
        path('fingerprint-scan/', views.fingerprint_scan, name='fingerprint_scan'),
        path('get-latest-fingerprint/', views.get_latest_fingerprint, name='get_latest_fingerprint'),
        path('verify-fingerprint/', views.verify_fingerprint, name='verify_fingerprint'),
        path('check-duplicate-fingerprint/', views.check_duplicate_fingerprint, name='check_duplicate_fingerprint'),
        path('authenticate-voter/', views.authenticate_voter, name='authenticate_voter'),
        path('submit-vote/', views.submit_vote, name='submit_vote'),
    ])),
]

urlpatterns += [
    path('register_voter_with_fingerprint/', register_voter_with_fingerprint, name='register_voter_with_fingerprint'),
    path('fingerprint_authenticate/', fingerprint_authenticate, name='fingerprint_authenticate'),
]
