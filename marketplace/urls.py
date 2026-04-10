from django.urls import path
from . import views

urlpatterns = [
    # Landing page — college selector
    path('', views.college_select_view, name='college_select'),

    # College-scoped pages
    path('c/<slug:slug>/', views.college_home_view, name='college_home'),
    path('c/<slug:slug>/listings/', views.listings_view, name='listings'),
    path('c/<slug:slug>/listing/<int:pk>/', views.listing_detail_view, name='listing_detail'),
    path('c/<slug:slug>/sell/', views.create_listing_view, name='create_listing'),
    path('c/<slug:slug>/listing/<int:pk>/message/', views.send_message_view, name='send_message'),
    path('c/<slug:slug>/listing/<int:pk>/poll/', views.poll_messages_view, name='poll_messages'),
    path('c/<slug:slug>/listing/<int:pk>/edit/', views.edit_listing_view, name='edit_listing'),
    path('c/<slug:slug>/listing/<int:pk>/sold/', views.mark_sold_view, name='mark_sold'),
    path('c/<slug:slug>/listing/<int:pk>/delete/', views.delete_listing_view, name='delete_listing'),

    # AJAX endpoints
    path('api/wishlist/<int:pk>/toggle/', views.toggle_wishlist_view, name='toggle_wishlist'),
]
