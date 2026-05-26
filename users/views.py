from django.shortcuts import render, redirect
from django.contrib.auth.models import User
# BƯỚC 1: Giữ nguyên các import cũ của bạn
from django.contrib.auth import authenticate, login, logout 
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
import logging

# THÊM MỚI: Import thêm thư viện gửi mail và Model OTP
from django.core.mail import send_mail
from .models import PasswordResetOTP, UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash


logger = logging.getLogger(__name__)

# HÀM XỬ LÝ ĐĂNG KÝ (GIỮ NGUYÊN)
def register_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirm_password') or ''

        if not username:
            messages.error(request, 'Tên đăng nhập không được để trống!')
            return redirect('register')

        if not email:
            messages.error(request, 'Email không được để trống!')
            return redirect('register')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Email không hợp lệ!')
            return redirect('register')

        if password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không khớp!')
            return redirect('register')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, ' '.join(e.messages))
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Tên đăng nhập đã tồn tại!')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email này đã được sử dụng!')
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        
        messages.success(request, 'Đăng ký thành công! Vui lòng đăng nhập.')
        return redirect('login')

    return render(request, 'register.html')


# HÀM XỬ LÝ ĐĂNG NHẬP (GIỮ NGUYÊN)
def login_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        if not username or not password:
            messages.error(request, 'Vui lòng nhập cả tên đăng nhập và mật khẩu.')
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home') 
        else:
            messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu!')

    return render(request, 'login.html')


# HÀM ĐĂNG XUẤT (GIỮ NGUYÊN)
def logout_view(request):
    logout(request) 
    return redirect('home') 


# ============================================================
# PHẦN THÊM MỚI: LOGIC QUÊN MẬT KHẨU (OTP)
# ============================================================

# 1. Nhập email và gửi OTP
def forgot_password_view(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        
        if user:
            # Lấy hoặc tạo mới bản ghi OTP cho người dùng
            otp_obj, created = PasswordResetOTP.objects.get_or_create(user=user)
            otp_obj.generate_otp()
            
            # Gửi mail thực tế
            subject = '[Shoestore] Mã OTP đặt lại mật khẩu'
            message = f'Chào {user.username}, mã xác thực của bạn là: {otp_obj.otp}. Vui lòng không cung cấp mã này cho người khác.'
            
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                request.session['reset_email'] = user.email # Lưu email vào phiên làm việc
                request.session.pop('debug_reset_otp', None)
                if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                    request.session['debug_reset_otp'] = otp_obj.otp
                    messages.warning(request, 'Hệ thống đang chạy local: OTP được in trong terminal chạy server, không gửi về email thật.')
                return redirect('verify_otp')
            except Exception as e:
                logger.exception('Send OTP email failed: %s', e)
                if settings.DEBUG:
                    # Fallback cho môi trường dev để vẫn test được luồng quên mật khẩu.
                    request.session['reset_email'] = email
                    request.session['debug_reset_otp'] = otp_obj.otp
                    messages.warning(request, f'Không gửi được email. Mã OTP test của bạn là: {otp_obj.otp}')
                    return redirect('verify_otp')
                messages.error(request, 'Lỗi hệ thống không thể gửi mail. Vui lòng thử lại sau!')
        else:
            messages.error(request, 'Email này chưa được đăng ký trong hệ thống!')
            
    return render(request, 'users/forgot_password.html')


# 2. Xác nhận OTP
def verify_otp_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    user = User.objects.filter(email=email).first()
    if not user:
        request.session.pop('reset_email', None)
        request.session.pop('debug_reset_otp', None)
        messages.error(request, 'Phiên đặt lại mật khẩu đã hết hạn. Vui lòng thử lại.')
        return redirect('forgot_password')

    if request.method == 'POST':
        otp_input = (request.POST.get('otp') or '').strip()
        if not otp_input.isdigit() or len(otp_input) != 6:
            messages.error(request, 'OTP phải gồm đúng 6 chữ số!')
            return render(request, 'users/verify_otp.html')

        # Kiểm tra mã OTP trong database
        otp_record = PasswordResetOTP.objects.filter(user=user, otp=otp_input).first()

        if otp_record:
            return redirect('reset_password')
        else:
            messages.error(request, 'Mã OTP bạn nhập không chính xác!')
            
    return render(request, 'users/verify_otp.html')


# 3. Thiết lập mật khẩu mới
def reset_password_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password == confirm_password:
            try:
                # Kiểm tra độ mạnh mật khẩu mới
                validate_password(password)
                
                user = User.objects.get(email=email)
                user.set_password(password) # Mã hóa mật khẩu mới
                user.save()
                
                # Xóa OTP đã dùng và dọn dẹp session
                PasswordResetOTP.objects.filter(user=user).delete()
                del request.session['reset_email']
                request.session.pop('debug_reset_otp', None)
                
                messages.success(request, 'Đặt lại mật khẩu thành công! Hãy đăng nhập với mật khẩu mới.')
                return redirect('login')
            except ValidationError as e:
                messages.error(request, ' '.join(e.messages))
        else:
            messages.error(request, 'Mật khẩu xác nhận không trùng khớp!')

    return render(request, 'users/reset_password.html')


# ============================================================
# PHẦN THÊM MỚI: THÔNG TIN CÁ NHÂN (PROFILE)
# ============================================================
@login_required(login_url='login')
def profile_view(request):
    user = request.user
    # Lấy hoặc tạo Profile cho user nếu chưa có
    profile, created = UserProfile.objects.get_or_create(user=user)

    # TỰ ĐỘNG ĐIỀN DỮ LIỆU TỪ LSQĐ NẾU PROFILE TRỐNG
    if not profile.phone or not profile.address or not user.first_name:
        from orders.models import Order # Import model Order
        last_order = Order.objects.filter(user=user).order_by('-created_at').first()
        if last_order:
            if not profile.phone and last_order.phone:
                profile.phone = last_order.phone
            if not profile.address and last_order.address:
                profile.address = last_order.address
            profile.save()
            
            if not user.first_name and last_order.full_name:
                parts = last_order.full_name.split(' ', 1)
                user.first_name = parts[0]
                if len(parts) > 1:
                    user.last_name = parts[1]
                user.save()

    if request.method == 'POST':
        # Cập nhật thông tin cơ bản
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Cập nhật thông tin profile
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        # Xử lý cập nhật mật khẩu (nếu có yêu cầu đổi)
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        has_error = False

        # Kiểm tra email trùng lặp (nếu đổi email)
        if email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                messages.error(request, 'Email này đã được sử dụng bởi tài khoản khác!')
                has_error = True
            else:
                try:
                    validate_email(email)
                    user.email = email
                except ValidationError:
                    messages.error(request, 'Email không hợp lệ!')
                    has_error = True

        if not has_error:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            profile.phone = phone
            profile.address = address
            profile.save()

            # Nếu người dùng có nhập mật khẩu cũ, coi như họ muốn đổi mật khẩu
            if old_password:
                if user.check_password(old_password):
                    if new_password and new_password == confirm_password:
                        try:
                            # Kiểm tra độ mạnh của mật khẩu mới
                            validate_password(new_password, user)
                            user.set_password(new_password)
                            user.save()
                            # Giữ trạng thái đăng nhập sau khi đổi mật khẩu
                            update_session_auth_hash(request, user)
                            messages.success(request, 'Cập nhật thông tin và mật khẩu thành công!')
                        except ValidationError as e:
                            messages.error(request, ' '.join(e.messages))
                    else:
                        messages.error(request, 'Mật khẩu mới và mật khẩu xác nhận không trùng khớp hoặc bị trống!')
                else:
                    messages.error(request, 'Mật khẩu cũ không chính xác!')
            else:
                messages.success(request, 'Cập nhật thông tin cá nhân thành công!')

        return redirect('profile')

    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'users/profile.html', context)