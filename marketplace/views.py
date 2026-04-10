from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from core.models import College, Listing, WishlistItem, Message, UserProfile


def college_select_view(request):
    """Landing page — choose a college marketplace to browse."""
    colleges = College.objects.filter(is_active=True).annotate(
        member_count=Count('members'),
        listing_count=Count('listings', filter=Q(listings__is_active=True, listings__is_sold=False))
    )
    context = {
        'colleges': colleges,
        'total_listings': Listing.objects.filter(is_active=True, is_sold=False).count(),
        'total_users': UserProfile.objects.count(),
    }
    return render(request, 'marketplace/college_select.html', context)


def college_home_view(request, slug):
    """Home page scoped to a specific college's marketplace."""
    college = get_object_or_404(College, slug=slug, is_active=True)
    listings = Listing.objects.filter(college=college, is_active=True, is_sold=False)

    # Category counts for this college
    categories = [
        {'id': cat[0], 'emoji': Listing.CATEGORY_EMOJIS.get(cat[0], '📦'),
         'count': listings.filter(category=cat[0]).count()}
        for cat in Listing.CATEGORY_CHOICES
    ]

    # Trending = most views, Latest = most recent
    trending = listings.order_by('-views')[:8]
    latest = listings.order_by('-created_at')[:8]

    # Wishlist IDs for current user
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('listing_id', flat=True))

    # Stats
    member_count = UserProfile.objects.filter(college=college).count()
    listing_count = listings.count()

    context = {
        'college': college,
        'categories': categories,
        'trending': trending,
        'latest': latest,
        'wishlist_ids': wishlist_ids,
        'member_count': member_count,
        'listing_count': listing_count,
    }
    return render(request, 'marketplace/home.html', context)


def listings_view(request, slug):
    """Browse all listings for a college with filters."""
    college = get_object_or_404(College, slug=slug, is_active=True)
    listings = Listing.objects.filter(college=college, is_active=True, is_sold=False)

    # Apply filters
    category = request.GET.get('category', '')
    condition = request.GET.get('condition', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    search = request.GET.get('q', '')
    sort = request.GET.get('sort', 'latest')

    if category:
        listings = listings.filter(category=category)
    if condition:
        listings = listings.filter(condition=condition)
    if price_min:
        try:
            listings = listings.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            listings = listings.filter(price__lte=float(price_max))
        except ValueError:
            pass
    if search:
        listings = listings.filter(
            Q(title__icontains=search) | Q(description__icontains=search) | Q(category__icontains=search)
        )

    # Sorting
    if sort == 'price-asc':
        listings = listings.order_by('price')
    elif sort == 'price-desc':
        listings = listings.order_by('-price')
    elif sort == 'popular':
        listings = listings.order_by('-views')
    else:
        listings = listings.order_by('-created_at')

    # Wishlist IDs
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('listing_id', flat=True))

    context = {
        'college': college,
        'listings': listings,
        'wishlist_ids': wishlist_ids,
        'current_category': category,
        'current_condition': condition,
        'current_price_min': price_min,
        'current_price_max': price_max,
        'current_search': search,
        'current_sort': sort,
        'result_count': listings.count(),
        'categories': Listing.CATEGORY_CHOICES,
        'conditions': Listing.CONDITION_CHOICES,
    }
    return render(request, 'marketplace/listings.html', context)


def listing_detail_view(request, slug, pk):
    """Product detail page with seller info."""
    college = get_object_or_404(College, slug=slug, is_active=True)
    listing = get_object_or_404(Listing, pk=pk, college=college)

    # Track views (session-based to avoid inflation)
    viewed_key = f'viewed_{pk}'
    if not request.session.get(viewed_key):
        listing.views += 1
        listing.save(update_fields=['views'])
        request.session[viewed_key] = True

    # Check if wishlisted
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = WishlistItem.objects.filter(user=request.user, listing=listing).exists()

    # Related listings (same category, same college)
    related = Listing.objects.filter(
        college=college, category=listing.category, is_active=True, is_sold=False
    ).exclude(pk=pk)[:4]

    # Chat messages if user is logged in and is buyer or seller
    chat_messages = []
    if request.user.is_authenticated:
        chat_messages = Message.objects.filter(
            listing=listing
        ).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).order_by('created_at')[:50]

    context = {
        'college': college,
        'listing': listing,
        'is_wishlisted': is_wishlisted,
        'related': related,
        'chat_messages': chat_messages,
    }
    return render(request, 'marketplace/detail.html', context)


@login_required
def create_listing_view(request, slug):
    """Post a new listing — auto-scoped to user's college."""
    college = get_object_or_404(College, slug=slug, is_active=True)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '')
        original_price = request.POST.get('original_price', '')
        category = request.POST.get('category', '')
        condition = request.POST.get('condition', 'Good')
        location = request.POST.get('location', '').strip()
        image = request.FILES.get('image')

        # Validation
        errors = []
        if not title:
            errors.append('Title is required.')
        if not description:
            errors.append('Description is required.')
        if not price:
            errors.append('Price is required.')
        if not category:
            errors.append('Category is required.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                listing = Listing.objects.create(
                    seller=request.user,
                    college=college,
                    title=title,
                    description=description,
                    price=float(price),
                    original_price=float(original_price) if original_price else None,
                    category=category,
                    condition=condition,
                    location=location,
                    image=image,
                )
                messages.success(request, 'Your listing has been posted! 🎉')
                return redirect('listing_detail', slug=college.slug, pk=listing.pk)
            except (ValueError, Exception) as e:
                messages.error(request, f'Error creating listing: {str(e)}')

    context = {
        'college': college,
        'categories': Listing.CATEGORY_CHOICES,
        'conditions': Listing.CONDITION_CHOICES,
    }
    return render(request, 'marketplace/sell.html', context)


@login_required
def toggle_wishlist_view(request, pk):
    """AJAX endpoint to toggle wishlist status."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    listing = get_object_or_404(Listing, pk=pk)
    item, created = WishlistItem.objects.get_or_create(user=request.user, listing=listing)

    if not created:
        item.delete()
        return JsonResponse({'status': 'removed', 'wishlisted': False})
    return JsonResponse({'status': 'added', 'wishlisted': True})


@login_required
def send_message_view(request, slug, pk):
    """Send a message about a listing."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    listing = get_object_or_404(Listing, pk=pk)
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    Message.objects.create(
        sender=request.user,
        receiver=listing.seller,
        listing=listing,
        content=content,
    )
    return JsonResponse({'status': 'sent'})


@login_required
def mark_sold_view(request, slug, pk):
    """Mark a listing as sold."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    listing.is_sold = True
    listing.save(update_fields=['is_sold'])
    messages.success(request, f'"{listing.title}" has been marked as sold! 🎉')
    return redirect('profile')


@login_required
def delete_listing_view(request, slug, pk):
    """Delete a listing."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    listing.is_active = False
    listing.save(update_fields=['is_active'])
    messages.success(request, f'"{listing.title}" has been removed.')
    return redirect('profile')
