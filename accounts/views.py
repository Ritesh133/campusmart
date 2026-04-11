from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import UserProfile, Listing, WishlistItem
from .forms import SignupForm, LoginForm


import os
import requests

def signup_view(request):
    """Handle user registration with college selection and Supabase Auth."""
    if request.user.is_authenticated:
        return redirect('college_select')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']

            SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jixuwhmmzdxdrswaeplc.supabase.co')
            SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
            requires_confirmation = False

            if SUPABASE_KEY:
                # Register with Supabase Auth
                res = requests.post(
                    f"{SUPABASE_URL}/auth/v1/signup",
                    headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'},
                    json={'email': email, 'password': password},
                    timeout=10
                )
                if res.status_code not in (200, 201):
                    error_msg = res.json().get('msg', 'Registration failed with Supabase.')
                    messages.error(request, f"Signup Error: {error_msg}")
                    return render(request, 'auth/signup.html', {'form': form})
                
                # The GoTrue API returns a user directly or within a data dict.
                # If there's no session / access_token, it means confirmation is required.
                data = res.json()
                requires_confirmation = data.get('access_token') is None and data.get('session') is None

            # Use email prefix as username (unique)
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data.get('last_name', ''),
            )
            UserProfile.objects.create(
                user=user,
                college=form.cleaned_data['college'],
            )

            if SUPABASE_KEY and requires_confirmation:
                messages.success(request, 'Registration successful! A confirmation email has been sent. Please confirm your email first before logging in.')
                return redirect('login')
            else:
                # Auto login directly if no confirmation is required
                login(request, user)
                messages.success(request, f'Welcome to CampusMart, {user.first_name}! 🎉')
                return redirect('college_home', slug=form.cleaned_data['college'].slug)
    else:
        form = SignupForm()

    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    """Handle user login via email + password."""
    if request.user.is_authenticated:
        return redirect('college_select')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            
            SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jixuwhmmzdxdrswaeplc.supabase.co')
            SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

            user = None

            if SUPABASE_KEY:
                # Authenticate with Supabase
                res = requests.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'},
                    json={'email': email, 'password': password},
                    timeout=10
                )
                if res.status_code == 200:
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        user = None
                else:
                    error_msg = res.json().get('error_description', 'Invalid email or password.')
                    if 'Email not confirmed' in error_msg:
                        error_msg = 'Please confirm your email first!'
                    messages.error(request, error_msg)
            else:
                # Fallback to Django auth
                try:
                    user_obj = User.objects.get(email=email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
                
                if user is None:
                    messages.error(request, 'Invalid email or password.')

            if user is not None:
                # We need to set backend if authenticate() wasn't used
                if not hasattr(user, 'backend'):
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
                # Redirect to their college marketplace
                if hasattr(user, 'profile') and user.profile.college:
                    return redirect('college_home', slug=user.profile.college.slug)
                return redirect('college_select')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Log the user out."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('college_select')


def forgot_password_view(request):
    """Send Supabase password recovery email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jixuwhmmzdxdrswaeplc.supabase.co')
        SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
        
        if SUPABASE_KEY and email:
            # Construct redirect URL for password update page
            from django.urls import reverse
            redirect_to = request.build_absolute_uri(reverse('update_password'))
            
            # Auth endpoints require Bearer token and apikey
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json'
            }
            res = requests.post(
                f"{SUPABASE_URL}/auth/v1/recover",
                headers=headers,
                json={'email': email, 'data': {'redirectTo': redirect_to}},
                timeout=10
            )
            
            if res.status_code not in (200, 201, 204):
                error_info = res.json().get('msg') or res.json().get('error_description') or res.text
                messages.error(request, f"Supabase Error ({res.status_code}): {error_info}")
                print(f"DEBUG: Supabase recover failed for {email}: {res.status_code} - {res.text}")
            else:
                messages.success(request, "If that email is registered, we've sent a password reset link.")
        else:
            messages.error(request, "Supabase configuration missing or email empty.")
            
        return redirect('login')
    
    return render(request, 'auth/forgot_password.html')


import json
from django.http import JsonResponse

def update_password_view(request):
    """Renders the update password form. Handles proxying the token to Supabase."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            access_token = data.get('access_token')
            new_password = data.get('password')
            
            SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://jixuwhmmzdxdrswaeplc.supabase.co')
            SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

            if not access_token or not new_password:
                return JsonResponse({'success': False, 'error': 'Missing token or password'})

            # Use the user's access token to update their password
            res = requests.put(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
                json={'password': new_password},
                timeout=10
            )

            if res.status_code == 200:
                user_data = res.json()
                email = user_data.get('email')
                if email:
                    try:
                        u = User.objects.get(email=email)
                        u.set_password(new_password)
                        u.save(update_fields=['password'])
                    except User.DoesNotExist:
                        pass
                return JsonResponse({'success': True})
            else:
                error = res.json().get('msg') or res.json().get('error_description') or 'Failed to update password'
                return JsonResponse({'success': False, 'error': error})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'auth/update_password.html')


@login_required
def profile_view(request):
    """Display user profile with their listings, wishlist, sold items, and message inbox."""
    from core.models import Message
    from django.db.models import Max, Subquery, OuterRef

    profile = request.user.profile if hasattr(request.user, 'profile') else None
    my_listings = Listing.objects.filter(seller=request.user)
    wishlist_ids = WishlistItem.objects.filter(user=request.user).values_list('listing_id', flat=True)
    wishlist_listings = Listing.objects.filter(id__in=wishlist_ids)

    # Build inbox: group messages by (listing, other_user), show latest per thread
    all_messages = Message.objects.filter(
        receiver=request.user
    ).select_related('sender', 'listing', 'listing__college').order_by('-created_at')

    # Deduplicate: one entry per (listing, sender) pair
    seen = set()
    inbox_threads = []
    for msg in all_messages:
        key = (msg.listing_id, msg.sender_id)
        if key not in seen:
            seen.add(key)
            inbox_threads.append({
                'listing': msg.listing,
                'other_user': msg.sender,
                'last_msg': msg,
            })

    unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()

    context = {
        'profile': profile,
        'my_listings': my_listings,
        'wishlist_listings': wishlist_listings,
        'listings_count': my_listings.count(),
        'wishlist_count': wishlist_listings.count(),
        'inbox_threads': inbox_threads,
        'unread_count': unread_count,
    }
    return render(request, 'marketplace/profile.html', context)
