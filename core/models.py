from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class College(models.Model):
    """A college/university whose students can trade on CampusMart."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    logo_emoji = models.CharField(max_length=10, default='🏫')
    accent_color = models.CharField(max_length=7, default='#4F46E5', help_text='Hex color for branding')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Extended profile linked to Django's built-in User model."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True, max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} @ {self.college.name if self.college else 'No College'}"

    @property
    def initial(self):
        return self.user.first_name[0].upper() if self.user.first_name else self.user.username[0].upper()

    @property
    def display_name(self):
        full = self.user.get_full_name()
        return full if full else self.user.username


class Listing(models.Model):
    """An item listed for sale on a college marketplace."""
    CATEGORY_CHOICES = [
        ('Textbooks', 'Textbooks'),
        ('Electronics', 'Electronics'),
        ('Furniture', 'Furniture'),
        ('Clothing', 'Clothing'),
        ('Sports', 'Sports'),
        ('Stationery', 'Stationery'),
        ('Kitchen', 'Kitchen'),
        ('Vehicles', 'Vehicles'),
        ('Musical', 'Musical'),
        ('Other', 'Other'),
    ]
    CONDITION_CHOICES = [
        ('Like New', 'Like New'),
        ('Good', 'Good'),
        ('Fair', 'Fair'),
        ('Heavily Used', 'Heavily Used'),
    ]
    CATEGORY_EMOJIS = {
        'Textbooks': '📚', 'Electronics': '💻', 'Furniture': '🛋️',
        'Clothing': '👕', 'Sports': '⚽', 'Stationery': '✏️',
        'Kitchen': '🍳', 'Vehicles': '🚲', 'Musical': '🎸', 'Other': '📦',
    }

    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='Good')
    location = models.CharField(max_length=200, blank=True, help_text='Pickup spot on campus')
    image = models.ImageField(upload_to='listings/', null=True, blank=True)  # Legacy - kept for migration compat
    image_url = models.URLField(max_length=500, null=True, blank=True)  # Supabase public URL
    is_sold = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} — ₹{self.price}"

    @property
    def emoji(self):
        return self.CATEGORY_EMOJIS.get(self.category, '📦')

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    @property
    def time_ago(self):
        from django.utils import timezone
        delta = timezone.now() - self.created_at
        if delta.days > 30:
            return f"{delta.days // 30}mo ago"
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        return "Just now"


class WishlistItem(models.Model):
    """Tracks which listings a user has saved/wishlisted."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ♥ {self.listing.title}"


class Message(models.Model):
    """Chat message between buyer and seller about a listing."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}: {self.content[:50]}"
