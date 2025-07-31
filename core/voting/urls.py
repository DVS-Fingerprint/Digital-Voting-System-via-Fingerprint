from django.urls import path, include
from . import views

app_name = 'voting'

urlpatterns = [
    #ui views
    path('', views.home, name='home'),
    path('scanner/', views.scanner, name='scanner'),
    path('voter-home/', views.voter_home, name='voter_home'),
    path('vote/', views.election_view, name='election_view'),
    path('cast-vote/', views.vote_page, name='vote_page'),
    path('vote-success/', views.vote_success, name='vote_success'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('thank-you/', views.thankyou, name='thankyou'),
    path('already-voted/', views.already_voted, name='already_voted'),
    path('logout/', views.logout_voter, name='logout_voter'),

   
    # Admin/Staff Views
    path('register-voter/', views.register_voter, name='register_voter'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ESP32 & Fingerprint Sensor API Endpoints
    
    path("api/upload-template/", views.upload_template, name="upload_template"),  # Receive fingerprint template from ESP32
    path("api/match-template/", views.match_template, name="match_template"),     # Match incoming fingerprint template
    path('api/trigger-scan/', views.trigger_scan, name='trigger_scan'),           # Create scan trigger (admin)
    path('api/scan-trigger/', views.get_scan_trigger, name='get_scan_trigger'),   # ESP32 polls this for scan trigger
    path('api/latest-scanned-template/', views.get_latest_scanned_template, name='get_latest_scanned_template'),  # Get latest scanned template

    # ==========================
    # Voting API Endpoints
    # Nested under /api/ for cleanliness
    # ==========================
    path('api/', include([
        path('posts/', views.posts_list, name='posts_list'),
        path('candidates/', views.candidates_list, name='candidates_list'),
        path('vote/', views.vote_view, name='vote'),
        path('results/', views.results_view, name='results'),
        path('register-candidate/', views.register_candidate, name='register_candidate'),
        path('dashboard-data/', views.dashboard_view, name='dashboard_data'),
        path('authenticate-fingerprint/', views.authenticate_fingerprint, name='authenticate_fingerprint'),
        # New fingerprint-based voting endpoints
        path('fingerprint-scan/', views.fingerprint_scan, name='fingerprint_scan'),
        path('get-latest-fingerprint/', views.get_latest_fingerprint, name='get_latest_fingerprint'),
        path('verify-fingerprint/', views.verify_fingerprint, name='verify_fingerprint'),
        path('check-duplicate-fingerprint/', views.check_duplicate_fingerprint, name='check_duplicate_fingerprint'),
        # New authentication and voting endpoints
        path('authenticate-voter/', views.authenticate_voter, name='authenticate_voter'),
        path('submit-vote/', views.submit_vote, name='submit_vote'),
        # New fingerprint verification and vote casting endpoints
        path('fingerprint-verification/', views.fingerprint_verification, name='fingerprint_verification'),
        path('cast-vote/', views.cast_vote, name='cast_vote'),
    ])),
]
