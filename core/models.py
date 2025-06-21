from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import date

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    vendor_approval_status = models.CharField(max_length=20, default='pending', choices=(
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ))

class Package(models.Model):
    vendor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'vendor'})
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField()  # Duration in days
    destination = models.CharField(max_length=100)
    image = models.ImageField(upload_to='packages/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    is_approved = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expiry_date

class PackageImage(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='package_images/')

    def __str__(self):
        return f"Image for {self.package.title}"

class Booking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'user'})
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    travelers = models.PositiveIntegerField(default=1)
    tour_date = models.DateField(default=date.today)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Booking for {self.package} by {self.user}"

class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)  # Allow null values
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} for Booking {self.booking.id if self.booking else 'Pending'}"