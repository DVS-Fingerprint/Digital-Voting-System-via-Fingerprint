from django.urls import path
from . import views

app_name = 'voting'

urlpatterns = [
    path('', views.home, name='home'),
    path('register-voter/', views.register_voter, name='register_voter'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    # API endpoints
    path('api/authenticate_fingerprint/', views.authenticate_fingerprint, name='api_authenticate_fingerprint'),
    path('api/posts/', views.posts_list, name='api_posts'),
    path('api/candidates/', views.candidates_list, name='api_candidates'),
    path('api/vote/', views.vote_view, name='api_vote'),
    path('api/results/', views.results_view, name='api_results'),
    path('api/register_candidate/', views.register_candidate, name='api_register_candidate'),
    path('api/dashboard/', views.dashboard_view, name='api_dashboard'),
]
