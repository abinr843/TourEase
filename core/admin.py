from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Package, Booking, Payment

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'role', 'vendor_approval_status', 'is_staff')
    list_filter = ('role', 'vendor_approval_status', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Custom fields', {'fields': ('role', 'vendor_approval_status')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'vendor_approval_status'),
        }),
    )
    search_fields = ('username', 'email')
    ordering = ('username',)
    actions = ['approve_vendors']

    def approve_vendors(self, request, queryset):
        # Only update users with role 'vendor' and vendor_approval_status 'pending'
        updated = queryset.filter(role='vendor', vendor_approval_status='pending').update(vendor_approval_status='approved')
        self.message_user(request, f"{updated} vendor(s) have been approved.")
    approve_vendors.short_description = "Approve selected vendors"

class PackageAdmin(admin.ModelAdmin):
    list_display = ('title', 'vendor', 'destination', 'price', 'duration', 'is_approved', 'expiry_date')
    list_filter = ('is_approved', 'destination', 'vendor')
    search_fields = ('title', 'destination', 'vendor__username')
    actions = ['approve_packages']

    def approve_packages(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected packages have been approved.")
    approve_packages.short_description = "Approve selected packages"

class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'package', 'booking_date', 'status')
    list_filter = ('status', 'booking_date')
    search_fields = ('user__username', 'package__title')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'razorpay_order_id', 'razorpay_payment_id', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id', 'booking__id')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Payment, PaymentAdmin)