from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Package, Booking, Payment,PackageImage
from django.utils import timezone
import razorpay
from django.conf import settings
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta,date


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def home(request):
    packages = Package.objects.filter(is_approved=True, expiry_date__gt=timezone.now())
    return render(request, 'home.html', {'packages': packages})

def about(request):
    return render(request,'about.html')
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = CustomUser.objects.create_user(username=username, email=email, password=password, role='user')
            login(request, user)
            return redirect('home')
    return render(request, 'register.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.role == 'vendor' and user.vendor_approval_status != 'approved':
                messages.error(request, 'Vendor account not yet approved')
                return redirect('login')
            return redirect('home')
        messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def vendor_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            user = CustomUser.objects.create_user(username=username, email=email, password=password, role='vendor', vendor_approval_status='pending')
            login(request, user)
            messages.success(request, 'Vendor registration submitted. Awaiting admin approval.')
            return redirect('home')
    return render(request, 'vendor_register.html')


@login_required
def user_dashboard(request):
    if request.user.role != 'user':
        messages.error(request, 'Access denied: This dashboard is for regular users only.')
        return redirect('home')
    bookings = Booking.objects.filter(user=request.user).select_related('package')
    payments = Payment.objects.filter(booking__in=bookings).select_related('booking')

    return render(request, 'user_dashboard.html', {
        'bookings': bookings,
        'payments': payments,
    })

@login_required
def profile_management(request):
    if request.user.role != 'user':
        messages.error(request, 'Access denied: This page is for regular users only.')
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')


        if username != request.user.username and CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose a different username.')
            return redirect('profile_management')


        request.user.username = username
        request.user.email = email
        if password:
            request.user.set_password(password)
        request.user.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('user_dashboard')

    return render(request, 'profile_management.html')
@login_required
def cancel_booking(request, booking_id):
    if request.user.role != 'user':
        messages.error(request, 'Access denied: This action is for regular users only.')
        return redirect('home')

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'pending':
        messages.error(request, 'Cannot cancel: Booking is not in pending status.')
        return redirect('user_dashboard')


    booking.status = 'cancelled'
    booking.save()


    payment = Payment.objects.filter(booking=booking).first()
    if payment:
        payment.status = 'cancelled'
        payment.save()
    messages.success(request, 'Booking cancelled successfully!')
    return redirect('user_dashboard')

@login_required
def package_list(request):
    packages = Package.objects.filter(is_approved=True, expiry_date__gt=timezone.now())
    return render(request, 'package_list.html', {'packages': packages})

@login_required
def package_detail(request, pk):
    package = get_object_or_404(Package, pk=pk, is_approved=True, expiry_date__gt=timezone.now())
    if not request.user.is_authenticated:
        return redirect('register')
    return render(request, 'package_detail.html', {'package': package})


@login_required
def book_package(request, package_id):
    package = get_object_or_404(Package, pk=package_id, is_approved=True, expiry_date__gt=datetime.now().date())

    if request.method == 'POST':
        travelers = request.POST.get('travelers', '1')
        tour_date = request.POST.get('date')

        print(f"Received travelers: {travelers}, tour_date: {tour_date}")


        try:
            travelers = int(travelers)
            if travelers < 1 or travelers > 10:
                print("Validation failed: Invalid number of travelers.")
                return render(request, 'book_package.html', {
                    'package': package,
                    'error': 'Number of travelers must be between 1 and 10.'
                })
        except ValueError:
            print("Validation failed: Travelers value error.")
            return render(request, 'book_package.html', {
                'package': package,
                'error': 'Invalid number of travelers.'
            })


        if not tour_date:
            print("Validation failed: Tour date is required.")
            return render(request, 'book_package.html', {
                'package': package,
                'error': 'Tour date is required.'
            })

        try:
            tour_date = datetime.strptime(tour_date, '%Y-%m-%d').date()
            if tour_date < datetime.now().date():
                print("Validation failed: Tour date in the past.")
                return render(request, 'book_package.html', {
                    'package': package,
                    'error': 'Tour date cannot be in the past.'
                })
        except ValueError:
            print("Validation failed: Invalid date format.")
            return render(request, 'book_package.html', {
                'package': package,
                'error': 'Invalid date format. Please use YYYY-MM-DD.'
            })


        price_in_inr = package.price
        total_base_price = price_in_inr * travelers
        taxes = total_base_price * Decimal('0.18')
        discount = Decimal('0')
        total_amount = total_base_price + taxes - discount
        amount_in_paise = int(total_amount * 100)

        print(
            f"Package price (INR): {package.price}, Travelers: {travelers}, Base Price (INR): {total_base_price}, Taxes: {taxes}, Total (INR): {total_amount}, Amount (paise): {amount_in_paise}"
        )


        try:
            razorpay_order = razorpay_client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'payment_capture': 1
            })
            print(f"Razorpay order created: {razorpay_order['id']}")
        except Exception as e:
            print(f"Razorpay order creation failed: {str(e)}")
            return render(request, 'book_package.html', {
                'package': package,
                'error': f'Razorpay order creation failed: {str(e)}'
            })


        try:
            payment = Payment.objects.create(
                booking=None,
                razorpay_order_id=razorpay_order['id'],
                amount=total_amount,
                status='pending'
            )
            print(f"Payment created: {payment.id}")
        except Exception as e:
            print(f"Payment creation failed: {str(e)}")
            return render(request, 'book_package.html', {
                'package': package,
                'error': f'Payment creation failed: {str(e)}'
            })


        request.session['pending_booking'] = {
            'package_id': package.id,
            'travelers': travelers,
            'tour_date': tour_date.isoformat(),
            'payment_id': payment.id
        }
        print("Session updated with pending_booking.")


        first_image = package.images.first()
        image_url = first_image.image.url if first_image else "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80"

        print("Rendering payment.html")
        return render(request, 'payment.html', {
            'package': package,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': amount_in_paise,
            'payment_id': payment.id,
            'travelers': travelers,
            'base_price': total_base_price,
            'taxes': taxes,
            'discount': discount,
            'total_amount': total_amount,
            'image_url': image_url
        })

    print("Rendering book_package.html (GET request)")
    return render(request, 'book_package.html', {
        'package': package,
        'price_in_inr': package.price
    })


@csrf_exempt
@login_required
def payment_success(request):
    if request.method == 'POST':

        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        payment_id = request.POST.get('payment_id')

        print(f"Received payment_id: {payment_id}")


        pending_booking = request.session.get('pending_booking')
        if not payment_id and pending_booking:
            payment_id = str(pending_booking.get('payment_id'))

        print(f"Final payment_id: {payment_id}")


        if not payment_id or not payment_id.isdigit():
            messages.error(request, 'Invalid payment ID.')
            return redirect('package_list')


        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
        except Exception as e:
            messages.error(request, f'Payment verification failed: {str(e)}')
            return redirect('package_list')


        try:
            payment = Payment.objects.get(id=payment_id, razorpay_order_id=razorpay_order_id, status='pending')
            print(f"Found payment: {payment.id}, Status: {payment.status}")
        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found or already processed.')
            return redirect('package_list')


        if not pending_booking or pending_booking['payment_id'] != payment.id:
            messages.error(request, 'Invalid booking session.')
            return redirect('package_list')


        try:
            package = Package.objects.get(id=pending_booking['package_id'])
            tour_date = datetime.strptime(pending_booking['tour_date'], '%Y-%m-%d').date()
            booking = Booking.objects.create(
                user=request.user,
                package=package,
                travelers=pending_booking['travelers'],
                tour_date=tour_date,
                status='confirmed'
            )
            print(f"Created booking: {booking.id}")
        except Exception as e:
            messages.error(request, f'Booking creation failed: {str(e)}')
            return redirect('package_list')


        try:
            payment.booking = booking
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'completed'
            payment.save()
            print(f"Updated payment: {payment.id}, New Status: {payment.status}")
        except Exception as e:
            print(f"Error updating payment: {str(e)}")
            messages.error(request, f'Failed to update payment: {str(e)}')
            return redirect('package_list')

        # Clear the session
        del request.session['pending_booking']

        messages.success(request, 'Payment successful! Your booking has been confirmed.')
        return redirect('user_dashboard')

    messages.error(request, 'Invalid request method.')
    return redirect('package_list')

@login_required
def vendor_dashboard(request):
    if request.user.role != 'vendor' or request.user.vendor_approval_status != 'approved':
        messages.error(request, 'Access denied')
        return redirect('home')
    packages = Package.objects.filter(vendor=request.user)
    total_packages = packages.count()
    active_bookings = Booking.objects.filter(package__vendor=request.user, status='confirmed').count()
    total_revenue = sum(
        payment.amount
        for package in packages
        for booking in package.booking_set.filter(status='confirmed')
        for payment in booking.payment_set.filter(status='completed')
    )
    return render(request, 'vendor_dashboard.html', {
        'packages': packages,
        'total_packages': total_packages,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
    })


@login_required
def package_edit(request, pk):
    if request.user.role != 'vendor' or request.user.vendor_approval_status != 'approved':
        messages.error(request, 'Access denied')
        return redirect('home')

    package = get_object_or_404(Package, pk=pk, vendor=request.user)

    if request.method == 'POST':

        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        duration = request.POST.get('duration')
        destination = request.POST.get('destination')
        expiry_date = request.POST.get('expiry_date')

        if not all([title, description, price, duration, destination, expiry_date]):
            messages.error(request, 'All fields are required.')
            return render(request, 'package_edit.html', {'package': package})

        package.title = title
        package.description = description
        package.price = price
        package.duration = duration
        destination = destination
        package.expiry_date = expiry_date
        package.is_approved = False
        package.save()


        delete_image_ids = request.POST.getlist('delete_images')
        if delete_image_ids:
            PackageImage.objects.filter(id__in=delete_image_ids, package=package).delete()


        new_images = request.FILES.getlist('images')
        for image in new_images:
            PackageImage.objects.create(package=package, image=image)

        messages.success(request, 'Package updated successfully. Awaiting admin approval.')
        return redirect('vendor_dashboard')

    return render(request, 'package_edit.html', {'package': package})
@login_required
def package_create(request):
    if request.user.role != 'vendor' or request.user.vendor_approval_status != 'approved':
        messages.error(request, 'Access denied')
        return redirect('home')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        duration = request.POST.get('duration')
        destination = request.POST.get('destination')
        expiry_date = request.POST.get('expiry_date')
        images = request.FILES.getlist('images')


        if not all([title, description, price, duration, destination, expiry_date]):
            messages.error(request, 'All fields are required.')
            return render(request, 'package_create.html')

        package = Package.objects.create(
            vendor=request.user,
            title=title,
            description=description,
            price=price,
            duration=duration,
            destination=destination,
            expiry_date=expiry_date,
            is_approved=False
        )


        for image in images:
            PackageImage.objects.create(package=package, image=image)

        messages.success(request, 'Package submitted for approval')
        return redirect('vendor_dashboard')

    return render(request, 'package_create.html')

@login_required
def vendor_bookings(request):
    if request.user.role != 'vendor' or request.user.vendor_approval_status != 'approved':
        messages.error(request, 'Access denied')
        return redirect('home')


    bookings = Booking.objects.filter(package__vendor=request.user)


    total_bookings = bookings.count()
    confirmed_bookings = bookings.filter(status='confirmed').count()
    pending_bookings = bookings.filter(status='pending').count()


    bookings_data = []
    for booking in bookings:

        duration_days = booking.package.duration if isinstance(booking.package.duration, int) else 0


        start_date = booking.tour_date if booking.tour_date else date.today()
        end_date = start_date + timedelta(days=duration_days)

        bookings_data.append({
            'booking': booking,
            'start_date': start_date,
            'end_date': end_date,
        })

    return render(request, 'vendor_bookings.html', {
        'bookings_data': bookings_data,
        'bookings': bookings,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, 'Access denied: You are not superuser.')
        return redirect('home')

    all_users = CustomUser.objects.all()
    pending_vendors = CustomUser.objects.filter(role='vendor', vendor_approval_status='pending')
    all_packages = Package.objects.all().select_related('vendor')
    pending_packages = Package.objects.filter(is_approved=False).select_related('vendor')
    all_bookings = Booking.objects.all().select_related('user', 'package')
    all_payments = Payment.objects.all().select_related('booking__user', 'booking__package')

    total_payments = all_payments.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role')
            if not all([username, email, password, role]):
                messages.error(request, 'All fields are required.')
            elif CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
            else:
                user = CustomUser.objects.create_user(username=username, email=email, password=password, role=role)
                if role == 'vendor':
                    user.vendor_approval_status = 'pending'
                    user.save()
                messages.success(request, 'User created successfully.')

        elif action == 'edit_user':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(CustomUser, pk=user_id)
            username = request.POST.get('username')
            email = request.POST.get('email')
            role = request.POST.get('role')
            password = request.POST.get('password')
            vendor_approval_status = request.POST.get('vendor_approval_status') if role == 'vendor' else None

            if not all([username, email, role]):
                messages.error(request, 'Username, email, and role are required.')
            else:
                user.username = username
                user.email = email
                user.role = role
                if role == 'vendor' and vendor_approval_status:
                    user.vendor_approval_status = vendor_approval_status
                if password:
                    user.set_password(password)
                user.save()
                messages.success(request, 'User updated successfully.')

        elif action == 'delete_user':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(CustomUser, pk=user_id)
            user.delete()
            messages.success(request, 'User deleted successfully.')

        elif action == 'edit_package':
            package_id = request.POST.get('package_id')
            package = get_object_or_404(Package, pk=package_id)
            required_fields = ['title', 'description', 'price', 'duration', 'destination', 'expiry_date']
            missing_fields = [field for field in required_fields if not request.POST.get(field)]

            if missing_fields:
                messages.error(request, f'Missing required fields: {", ".join(missing_fields)}.')
            else:
                try:
                    package.title = request.POST['title']
                    package.description = request.POST['description']
                    package.price = float(request.POST['price'])
                    package.duration = request.POST['duration']
                    package.destination = request.POST['destination']
                    package.expiry_date = request.POST['expiry_date']
                    package.is_approved = 'is_approved' in request.POST

                    # Handle image deletions
                    delete_image_ids = request.POST.getlist('delete_images')  # IDs of images to delete
                    if delete_image_ids:
                        PackageImage.objects.filter(id__in=delete_image_ids, package=package).delete()


                    new_images = request.FILES.getlist('images')
                    for image in new_images:
                        PackageImage.objects.create(package=package, image=image)

                    package.save()
                    messages.success(request, 'Package updated successfully.')
                except ValueError as e:
                    messages.error(request, f'Invalid data provided: {str(e)}')

        elif action == 'delete_package':
            package_id = request.POST.get('package_id')
            package = get_object_or_404(Package, pk=package_id)
            package.delete()
            messages.success(request, 'Package deleted successfully.')

        elif action == 'update_booking_status':
            booking_id = request.POST.get('booking_id')
            status = request.POST.get('status')
            booking = get_object_or_404(Booking, pk=booking_id)
            if status:
                booking.status = status
                booking.save()
                messages.success(request, 'Booking status updated successfully.')
            else:
                messages.error(request, 'Status is required.')

        elif action == 'approve_vendor':
            user_id = request.POST.get('user_id')
            vendor = get_object_or_404(CustomUser, pk=user_id, role='vendor')
            vendor.vendor_approval_status = 'approved'
            vendor.save()
            messages.success(request, 'Vendor approved.')

        elif action == 'approve_package':
            package_id = request.POST.get('package_id')
            package = get_object_or_404(Package, pk=package_id)
            package.is_approved = True
            package.save()
            messages.success(request, 'Package approved.')

        all_users = CustomUser.objects.all()
        pending_vendors = CustomUser.objects.filter(role='vendor', vendor_approval_status='pending')
        all_packages = Package.objects.all().select_related('vendor')
        pending_packages = Package.objects.filter(is_approved=False).select_related('vendor')
        all_bookings = Booking.objects.all().select_related('user', 'package')
        all_payments = Payment.objects.all().select_related('booking__user', 'booking__package')
        total_payments = all_payments.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    return render(request, 'admin_dashboard.html', {
        'all_users': all_users,
        'pending_vendors': pending_vendors,
        'all_packages': all_packages,
        'pending_packages': pending_packages,
        'all_bookings': all_bookings,
        'all_payments': all_payments,
        'total_payments': total_payments,
    })