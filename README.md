# CampusMart

CampusMart is a student-only campus marketplace built with Django and Django REST Framework.  
It allows IIIT Delhi students to list used items, discover listings, save wishlist items, and manage their profile.

## What This Project Does

- Provides a marketplace for second-hand items inside campus.
- Restricts registration to institute emails (`@iiitd.ac.in`).
- Supports item posting with image upload and listing metadata.
- Offers wishlist and basic chat APIs for buyer-seller interaction.
- Includes template-based frontend pages for home, auth, listings, item detail, sell, profile, and chat.

## Tech Stack

- Python 3.x
- Django 5.2.x
- Django REST Framework
- DRF Token Authentication
- MySQL (configured as default database)
- HTML/CSS/Vanilla JavaScript (Django templates)

## Project Structure

```text
CampusMart/
├── api/                    # Models, serializers, API viewsets, auth views, routes
├── campusmart_backend/     # Django settings, root urls, ASGI/WSGI
├── templates/campusmart/   # Frontend pages (home, listings, detail, sell, etc.)
├── media/                  # Uploaded listing images (created at runtime)
└── manage.py
```

## Core Features

1. **Authentication**
   - Register and login via token auth.
   - Registration allows only `@iiitd.ac.in` email addresses.

2. **Listings**
   - Create, read, update, delete listings.
   - Listing data includes title, category, condition, price, location, description, seller details, tags, and optional image.

3. **Wishlist**
   - Authenticated users can save and remove listing items from wishlist.

4. **Profile**
   - Returns user info, listings count, sold count, wishlist count, and user listings.

5. **Chat (basic)**
   - Chat message model and authenticated API endpoints are available.

## API Overview

Base URL: `http://localhost:8000/api/`

- `POST /auth/register/` - register user
- `POST /auth/login/` - login user
- `GET|POST /listings/` - list/create listings
- `GET|PUT|PATCH|DELETE /listings/{id}/` - listing detail/update/delete
- `GET|POST /wishlist/` - list/add wishlist entries (auth required)
- `DELETE /wishlist/remove_item/?listing_id={id}` - remove wishlist item (auth required)
- `GET|POST /chat/` - list/create messages (auth required)
- `GET /profile/` - user profile stats (auth required)

## Frontend Routes

- `/`
- `/login/`
- `/signup/`
- `/listings/`
- `/item/<id>/`
- `/sell/`
- `/profile/`
- `/chat/`

## Local Setup

### 1) Clone and enter project

```bash
git clone <your-repo-url>
cd CampusMart
```

### 2) Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

This project currently does not include a `requirements.txt`, so install the likely required packages manually:

```bash
pip install django djangorestframework django-cors-headers mysqlclient pillow
```

### 4) Configure MySQL database

Update database settings in `campusmart_backend/settings.py` if needed:

- DB name: `campusmart`
- User: `root`
- Host: `127.0.0.1`
- Port: `3306`

Create the database before migrations:

```sql
CREATE DATABASE campusmart;
```

### 5) Run migrations and start server

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

App will run at: `http://127.0.0.1:8000/`

## Notes / Current Gaps

- `settings.py` currently contains an extra closing brace in the `DATABASES` section that may need cleanup before running migrations.
- There is no pinned dependency file yet (`requirements.txt`), so environment reproducibility is limited.
- Security and production hardening (secret management, `DEBUG=False`, restricted CORS, proper `ALLOWED_HOSTS`) are still needed for deployment.

## Suggested Next Improvements

- Add `requirements.txt` and lock package versions.
- Add API tests for auth, listings, wishlist, and profile.
- Add proper chat UI integration and route consistency checks.
- Add deployment settings and environment-variable based config.
