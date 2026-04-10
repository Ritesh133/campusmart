from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import UserProfile, Listing, WishlistItem
from .forms import SignupForm, LoginForm


def signup_view(request):
    """Handle user registration with college selection."""
    if request.user.is_authenticated:
        return redirect('college_select')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
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
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data.get('last_name', ''),
            )
            UserProfile.objects.create(
                user=user,
                college=form.cleaned_data['college'],
            )
            # Auto login after signup
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
            # Find user by email
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
                # Redirect to their college marketplace
                if hasattr(user, 'profile') and user.profile.college:
                    return redirect('college_home', slug=user.profile.college.slug)
                return redirect('college_select')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Log the user out."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('college_select')


@login_required
def profile_view(request):
    """Display user profile with their listings, wishlist, sold items, and message inbox."""
    from core.models import Message
    from django.db.models import Max, Subquery, OuterRef

    profile = request.user.profile if hasattr(request.user, 'profile') else None
    my_listings = Listing.objects.filter(seller=request.user, is_active=True, is_sold=False)
    sold_listings = Listing.objects.filter(seller=request.user, is_sold=True)
    wishlist_ids = WishlistItem.objects.filter(user=request.user).values_list('listing_id', flat=True)
    wishlist_listings = Listing.objects.filter(id__in=wishlist_ids, is_active=True)

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
        'sold_listings': sold_listings,
        'wishlist_listings': wishlist_listings,
        'listings_count': my_listings.count(),
        'sold_count': sold_listings.count(),
        'wishlist_count': wishlist_listings.count(),
        'inbox_threads': inbox_threads,
        'unread_count': unread_count,
    }
    return render(request, 'marketplace/profile.html', context)
