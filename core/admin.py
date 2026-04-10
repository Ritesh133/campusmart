from django.contrib import admin
from .models import College, UserProfile, Listing, WishlistItem, Message


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'is_active', 'created_at')
    list_filter = ('is_active', 'state')
    search_fields = ('name', 'city')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'college', 'phone', 'created_at')
    list_filter = ('college',)
    search_fields = ('user__username', 'user__email')


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'college', 'price', 'category', 'condition', 'is_sold', 'views', 'created_at')
    list_filter = ('college', 'category', 'condition', 'is_sold', 'is_active')
    search_fields = ('title', 'description', 'seller__username')
    readonly_fields = ('views',)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'listing', 'created_at')
    list_filter = ('user',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'listing', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('content',)
