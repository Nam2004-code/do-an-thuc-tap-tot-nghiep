from django.db import models
from django.contrib.auth.models import User
import random

# Bảng lưu trữ lịch sử chat của từng người dùng (GIỮ NGUYÊN)
class ChatMessage(models.Model):
    # Liên kết với tài khoản khách hàng. null=True, blank=True để khách chưa đăng nhập vẫn có thể chat (nhưng không lưu)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(verbose_name="Nội dung tin nhắn")
    is_bot = models.BooleanField(default=False, verbose_name="Là tin nhắn của Bot?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Tự động sắp xếp tin nhắn cũ trước, mới sau để hiển thị đúng thứ tự

    def __str__(self):
        nguoi_gui = "Bot" if self.is_bot else "Khách"
        user_name = self.user.username if self.user else "Khách vãng lai"
        return f"[{nguoi_gui}] - {user_name} - {self.message[:30]}..."


# ============================================================
# PHẦN THÊM MỚI: MODEL LƯU TRỮ MÃ OTP QUÊN MẬT KHẨU
# ============================================================
class PasswordResetOTP(models.Model):
    # Liên kết mã OTP với một User cụ thể
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Mã xác nhận gồm 6 chữ số
    otp = models.CharField(max_length=6, verbose_name="Mã OTP")
    # Thời điểm tạo mã
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        """Hàm tự động tạo mã 6 số ngẫu nhiên"""
        self.otp = str(random.randint(100000, 999999))
        self.save()

    class Meta:
        # Sắp xếp mã mới nhất lên đầu
        ordering = ['-created_at']
        verbose_name = "Mã xác thực OTP"
        verbose_name_plural = "Mã xác thực OTP"

    def __str__(self):
        return f"OTP: {self.otp} - Tài khoản: {self.user.username}"


# ============================================================
# PHẦN THÊM MỚI: MODEL LƯU TRỮ THÔNG TIN CÁ NHÂN (PROFILE)
# ============================================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Số điện thoại")
    address = models.TextField(null=True, blank=True, verbose_name="Địa chỉ giao hàng")

    class Meta:
        verbose_name = "Thông tin cá nhân"
        verbose_name_plural = "Thông tin cá nhân"

    def __str__(self):
        return f"Profile của {self.user.username}"