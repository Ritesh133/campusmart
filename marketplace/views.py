from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from core.models import College, Listing, WishlistItem, Message, UserProfile
from marketplace.storage import upload_image_to_supabase, delete_image_from_supabase


def college_select_view(request):
    """Landing page — choose a college marketplace to browse."""
    colleges = College.objects.filter(is_active=True).annotate(
        member_count=Count('members', distinct=True),
        listing_count=Count('listings', filter=Q(listings__is_active=True, listings__is_sold=False), distinct=True)
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
    buyer_threads = []  # for seller's view: list of {buyer, messages}
    unread_from_buyers = 0

    if request.user.is_authenticated:
        if request.user == listing.seller:
            # Seller sees all conversations from all buyers
            all_msgs = Message.objects.filter(listing=listing).select_related('sender', 'receiver').order_by('created_at')
            # Group by buyer
            threads_map = {}
            for msg in all_msgs:
                buyer = msg.sender if msg.sender != listing.seller else msg.receiver
                if buyer.pk not in threads_map:
                    threads_map[buyer.pk] = {'buyer': buyer, 'messages': []}
                threads_map[buyer.pk]['messages'].append(msg)
            buyer_threads = list(threads_map.values())
            # Mark messages to seller as read
            Message.objects.filter(listing=listing, receiver=request.user, is_read=False).update(is_read=True)
            unread_from_buyers = 0  # just cleared
        else:
            # Buyer sees only their own thread with seller
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
        'buyer_threads': buyer_threads,
        'unread_from_buyers': unread_from_buyers,
    }
    return render(request, 'marketplace/detail.html', context)


@login_required
def create_listing_view(request, slug):
    # Force Redeploy - Fix for VariableDoesNotExist listing
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
                # Upload image to Supabase Storage (direct REST, no S3)
                image_url = None
                if image:
                    image_url = upload_image_to_supabase(image, folder='listings')

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
                    image_url=image_url,
                )
                messages.success(request, 'Your listing has been posted! 🎉')
                return redirect('listing_detail', slug=college.slug, pk=listing.pk)
            except (ValueError, Exception) as e:
                messages.error(request, f'Error creating listing: {str(e)}')

    context = {
        'college': college,
        'listing': None,
        'categories': Listing.CATEGORY_CHOICES,
        'conditions': Listing.CONDITION_CHOICES,
        'is_edit': False,
    }
    return render(request, 'marketplace/sell.html', context)


@login_required
def edit_listing_view(request, slug, pk):
    """Edit an existing listing."""
    college = get_object_or_404(College, slug=slug, is_active=True)
    listing = get_object_or_404(Listing, pk=pk, college=college, seller=request.user)

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
        if not title: errors.append('Title is required.')
        if not description: errors.append('Description is required.')
        if not price: errors.append('Price is required.')
        if not category: errors.append('Category is required.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                listing.title = title
                listing.description = description
                listing.price = float(price)
                listing.original_price = float(original_price) if original_price else None
                listing.category = category
                listing.condition = condition
                listing.location = location
                if image:
                    new_url = upload_image_to_supabase(image, folder='listings')
                    if new_url:
                        listing.image_url = new_url
                listing.save()
                messages.success(request, 'Listing updated successfully! 📝')
                return redirect('listing_detail', slug=college.slug, pk=listing.pk)
            except (ValueError, Exception) as e:
                messages.error(request, f'Error updating listing: {str(e)}')

    context = {
        'college': college,
        'listing': listing, # Preload the form
        'categories': Listing.CATEGORY_CHOICES,
        'conditions': Listing.CONDITION_CHOICES,
        'is_edit': True,
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
    """Send a message about a listing — handles both buyer→seller and seller→buyer."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    listing = get_object_or_404(Listing, pk=pk)
    content = request.POST.get('content', '').strip()

    if not content:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    # Determine direction: buyer messages seller, seller replies to a specific buyer
    if request.user == listing.seller:
        # Seller replying — buyer_id must be passed
        buyer_id = request.POST.get('buyer_id')
        if not buyer_id:
            return JsonResponse({'error': 'buyer_id required for seller reply'}, status=400)
        from django.contrib.auth.models import User as AuthUser
        try:
            receiver = AuthUser.objects.get(pk=buyer_id)
        except AuthUser.DoesNotExist:
            return JsonResponse({'error': 'Buyer not found'}, status=404)
    else:
        # Buyer messaging seller
        receiver = listing.seller

    Message.objects.create(
        sender=request.user,
        receiver=receiver,
        listing=listing,
        content=content,
    )
    return JsonResponse({
        'status': 'sent',
        'sender': request.user.get_full_name() or request.user.username,
    })


@login_required
def poll_messages_view(request, slug, pk):
    """AJAX polling endpoint — returns messages newer than a given timestamp."""
    listing = get_object_or_404(Listing, pk=pk)
    since = request.GET.get('since', '0')  # Unix timestamp in milliseconds
    from django.utils import timezone
    import datetime
    try:
        since_dt = timezone.datetime.fromtimestamp(float(since) / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        since_dt = timezone.datetime.min.replace(tzinfo=timezone.utc)

    # Fetch messages relevant to this user (buyer or seller)
    msgs = Message.objects.filter(
        listing=listing,
        created_at__gt=since_dt
    ).filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('created_at')

    return JsonResponse({
        'messages': [
            {
                'content': m.content,
                'is_mine': m.sender == request.user,
                'time': m.created_at.strftime('%I:%M %p'),
                'ts': int(m.created_at.timestamp() * 1000),
                'sender_name': m.sender.get_full_name() or m.sender.username,
            }
            for m in msgs
        ]
    })


@login_required
def mark_sold_view(request, slug, pk):
    """Mark a listing as sold — hard-deletes all related data and the listing itself."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    title = listing.title
    image_url = listing.image_url

    # Hard-delete: Django cascades FKs — Message and WishlistItem rows deleted automatically
    listing.delete()

    # Clean up image from Supabase Storage (fire-and-forget)
    if image_url:
        delete_image_from_supabase(image_url)

    messages.success(request, f'"{title}" has been marked as sold and removed. 🎉')
    return redirect('profile')


@login_required
def delete_listing_view(request, slug, pk):
    """Delete a listing — hard-deletes all related data and cleans up storage."""
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    title = listing.title
    image_url = listing.image_url

    # Hard-delete: cascades to Message and WishlistItem automatically
    listing.delete()

    # Clean up image from Supabase Storage (fire-and-forget)
    if image_url:
        delete_image_from_supabase(image_url)

    messages.success(request, f'"{title}" has been permanently deleted.')
    return redirect('profile')
