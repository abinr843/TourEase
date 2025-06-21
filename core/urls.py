from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('about/',views.about,name = 'about'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('profile/', views.profile_management, name='profile_management'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('vendor/package/edit/<int:pk>/', views.package_edit, name='package_edit'),
    path('packages/', views.package_list, name='package_list'),
    path('package/<int:pk>/', views.package_detail, name='package_detail'),
    path('book/<int:package_id>/', views.book_package, name='book_package'),
    path('vendor/register/', views.vendor_register, name='vendor_register'),
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/package/create/', views.package_create, name='package_create'),
    path('vendor/bookings/', views.vendor_bookings, name='vendor_bookings'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
]