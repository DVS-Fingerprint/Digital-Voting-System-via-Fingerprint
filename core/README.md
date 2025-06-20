# Fingerprint-Based Digital Voting System

## Overview
A secure, scalable digital voting system using fingerprint authentication (ESP32 + AS608), Django REST Framework backend, and a responsive web frontend.

## Features
- Voter authentication via fingerprint (ESP32)
- Web-based voting interface
- Admin dashboard with real-time results
- RESTful API endpoints
- Candidate images and party symbols
- Activity logging and export

## Tech Stack
- Backend: Django, Django REST Framework
- Frontend: HTML, CSS, JS (Bootstrap)
- Database: SQLite (dev), PostgreSQL (prod)
- Hardware: ESP32 + AS608

## Project Structure
- `core/` (Django project)
  - `voting/` (app: models, views, serializers, urls)
  - `templates/` (HTML frontend)
  - `static/` (CSS, JS, images)
  - `media/` (uploaded images)
- `requirements.txt`

> **Note:** Only the above folders are required. Remove any extra folders (e.g., 'User Interface').

## API Endpoints
- `POST /api/authenticate_fingerprint/` — Authenticate voter by UID
- `GET /api/posts/` — List election posts
- `GET /api/candidates/?post_id=1` — List candidates for a post
- `POST /api/vote/` — Submit votes
- `GET /api/results/` — (Admin) Results per candidate
- `POST /api/register_candidate/` — (Admin) Add candidate
- `GET /api/dashboard/` — (Admin) Summary stats

## Setup Instructions
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run migrations:
   ```bash
   python manage.py migrate
   ```
3. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```
4. Start the server:
   ```bash
   python manage.py runserver
   ```
5. Access admin at `/admin/` and API at `/api/`

## ESP32 Integration
- ESP32 sends POST to `/api/authenticate_fingerprint/` with `{ "uid": "F123456" }`
- See API docs for details

## Media & Static Files
- Candidate images and symbols are uploaded to `media/`
- Place custom CSS/JS/images in `static/` (create if missing)

## Deployment
- Use PostgreSQL for production
- Deploy with Gunicorn + Nginx or Render/Heroku

## License
MIT
