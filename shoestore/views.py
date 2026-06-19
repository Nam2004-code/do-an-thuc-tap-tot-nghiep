import os
import json
import logging
import re
import traceback
import urllib.parse
import hashlib
import hmac
import requests  # <-- Thêm thư viện requests để thực hiện HTTP POST request sang API SpeedSMS
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from dotenv import load_dotenv

# SỬ DỤNG THƯ VIỆN GROQ (SIÊU NHANH & MIỄN PHÍ)
from groq import Groq

from users.models import ChatMessage
from products.models import Product, Category, Brand 
from .models import Order  # Giả sử model Order nằm chung ứng dụng hoặc điều chỉnh sang: from orders.models import Order

logger = logging.getLogger(__name__)
load_dotenv() 

# Khởi tạo Groq Client
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    client = Groq(api_key=api_key)
else:
    client = None
    logger.warning("GROQ_API_KEY không được cấu hình trong .env; tính năng Groq chat sẽ tắt.")

# ==========================================
# 1. CÁC TRANG CƠ BẢN
# ==========================================

def home(request):
    sale_products = Product.objects.filter(old_price__gt=0).order_by('?')[:10]
    all_brands = Brand.objects.all()
    latest_products = Product.objects.all().order_by('-id')[:8]
    context = {
        'sale_products': sale_products, 
        'brands': all_brands, 
        'latest_products': latest_products
    }
    return render(request, 'home.html', context)

def help_page(request):
    return render(request, 'help.html')

def return_policy_page(request):
    return render(request, 'return_policy.html')

def warranty_policy_page(request):
    return render(request, 'warranty_policy.html')

def contact_page(request):
    return render(request, 'contact.html')

def sale_page(request):
    sale_items = Product.objects.filter(old_price__gt=0).order_by('-id')
    return render(request, 'sale.html', {'sale_items': sale_items})

def chatbot_index(request):
    return render(request, 'chatbot.html')


# ==========================================
# 2. TIỆN ÍCH & BẢO VỆ DATABASE & VNPAY SERVICE & SMS GATEWAY
# ==========================================

def clean_text_for_db(text):
    """Xóa các emoji để tránh lỗi MySQL 1366 khi lưu vào Database."""
    if not text:
        return ""
    # Chỉ giữ lại các ký tự thuộc chuẩn BMP (bao gồm tiếng Việt), loại bỏ emoji
    return ''.join(c for c in text if ord(c) < 0x10000)


def send_sms_notification(phone_number, order_id, total_price):
    """
    🔥 TÍNH NĂNG NÂNG CAO: Kết nối API SpeedSMS để tự động gửi thông báo thời gian thực
    """
    # Lấy thông tin cấu hình bảo mật từ settings hoặc biến môi trường .env
    api_key = os.getenv("SPEEDSMS_API_KEY", "MÃ_API_MẶC_ĐỊNH_NẾU_CHƯA_CÓ")
    sender_name = os.getenv("SPEEDSMS_SENDER", "SpeedSMS")
    url = "https://api.speedsms.vn/index.php/sms/send"
    
    if not phone_number:
        return False

    # Định dạng lại số điện thoại về chuẩn Quốc tế 84 theo yêu cầu nhà mạng (Ví dụ: 0905... -> 84905...)
    if phone_number.startswith('0'):
        phone_number = '84' + phone_number[1:]
        
    # Nội dung SMS Chăm sóc khách hàng bám sát nghiệp vụ đơn hàng
    content = f"Cam on ban da mua hang tai Shoe Store. Don hang #{order_id} tri gia {int(total_price):,} VND da duoc thanh toan va khoi tao thanh cong!"
    
    payload = {
        'to': phone_number,
        'content': content,
        'sms_type': 2,  # Loại 2: Tin nhắn Chăm sóc khách hàng (CSKH)
        'sender': sender_name
    }
    
    try:
        # Gọi HTTP POST Request sử dụng Basic Authentication (Tài liệu API SpeedSMS)
        response = requests.post(
            url, 
            json=payload, 
            auth=(api_key, 'x'),
            timeout=10
        )
        result = response.json()
        
        if result.get('status') == 'success':
            logger.info(f"--> [SMS] Gửi tin nhắn thành công cho đơn hàng #{order_id}")
            return True
        else:
            logger.error(f"--> [SMS] Lỗi phản hồi kết nối từ SpeedSMS: {result.get('message')}")
            return False
    except Exception as e:
        logger.error(f"--> [SMS] Thất bại khi kết nối tới máy chủ Gateway SMS: {str(e)}")
        return False


class VNPayService:
    """Lớp bổ trợ mã hóa dữ liệu theo thuật toán SHA512 bảo mật của VNPay"""
    def __init__(self, tmn_code, hash_secret, payment_url, return_url):
        self.tmn_code = tmn_code
        self.hash_secret = hash_secret
        self.payment_url = payment_url
        self.return_url = return_url

    def generate_payment_url(self, order_id, amount, order_desc, ip_address, create_date):
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.tmn_code,
            'vnp_Amount': int(amount * 100),  # VNPay yêu cầu nhân 100 số tiền
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': str(order_id),
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_Locale': 'vn',
            'vnp_ReturnUrl': self.return_url,
            'vnp_IpAddr': ip_address,
            'vnp_CreateDate': create_date,
        }
        sorted_params = sorted(vnp_params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        hmac_value = hmac.new(
            self.hash_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return f"{self.payment_url}?{query_string}&vnp_SecureHash={hmac_value}"

    def validate_response(self, response_data):
        vnp_secure_hash = response_data.get('vnp_SecureHash', '')
        params = {k: v for k, v in response_data.items() if k.startswith('vnp_') and k != 'vnp_SecureHash' and k != 'vnp_SecureHashType'}
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        calculated_hash = hmac.new(
            self.hash_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return calculated_hash == vnp_secure_hash


# ==========================================
# 3. XỬ LÝ CHATBOT AI VỚI GROQ (LLAMA 3)
# ==========================================

@csrf_exempt
def get_response(request):
    if request.method == 'POST':
        if not client:
            return JsonResponse({'error': 'Chưa cấu hình Groq API Key.'}, status=503)
        
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            display_message = data.get('display_message', user_message)
            
            if not user_message:
                return JsonResponse({'error': 'Tin nhắn trống.'}, status=400)

            # Lưu tin nhắn khách hàng 
            user = request.user if request.user.is_authenticated else None
            if user:
                ChatMessage.objects.create(
                    user=user, 
                    message=clean_text_for_db(display_message), 
                    is_bot=False
                )

            # Lấy dữ liệu sản phẩm CÓ BAO GỒM LINK ẢNH
            products = Product.objects.filter(is_active=True)
            products_context = ""
            for p in products:
                sizes = ", ".join([s.value for s in p.sizes.all()]) if p.sizes.exists() else "Đủ size"
                brand = p.brand.name if p.brand else "Store"
                cate = p.category.name if p.category else "Giày"
                img_url = p.image.url if getattr(p, 'image', None) else ""
                
                products_context += f"- Mã SP: {p.id}. Tên: {p.name}. Loại: {cate}. Hãng: {brand}. Giá: {p.price} VNĐ. Size hiện có: {sizes}. Hình ảnh: {img_url}. Mô tả: {p.description}\n"

            # DẠY AI: CHUYÊN VIÊN TƯ VẤN CAO CẤP
            is_authenticated = request.user.is_authenticated
            auth_status = "ĐÃ ĐĂNG NHẬP" if is_authenticated else "CHƯA ĐĂNG NHẬP"

            system_prompt = f"""
            Bạn là chuyên viên tư vấn bán hàng cao cấp của Shoe Store - "Nâng bước thành công".
            
            🌟 THÔNG TIN CỬA HÀNG & KHÁCH HÀNG:
            - Địa chỉ: Quận Hải Châu, TP. Đà Nẵng | Hotline: 0905.123.456
            - Khách hàng đang chat ở trạng thái: {auth_status}

            🎯 KỸ NĂNG TƯ VẤN & BÁN HÀNG:
            1. GIỚI THIỆU SẢN PHẨM: Trình bày in đậm tên sản phẩm, dùng gạch đầu dòng, chèn emoji (👟, 🔥, ✨).
            2. HIỂN THỊ HÌNH ẢNH: BẮT BUỘC chèn đoạn mã: [SHOW_IMAGE: Đường_Dẫn_Hình_Ảnh] khi được yêu cầu xem hình.
            3. QUY TẮC THÊM VÀO GIỎ HÀNG (QUAN TRỌNG NHẤT):
               - NẾU KHÁCH HÀNG "CHƯA ĐĂNG NHẬP": BẠN TUYỆT ĐỐI KHÔNG cho khách thêm vào giỏ. Bất kỳ yêu cầu mua hàng nào cũng phải bị từ chối: "Xin lỗi, hãy đăng kí hoặc đăng nhập rồi mới thêm giỏ hàng được nhé!". KHÔNG cấp bất kỳ mã nào.
               - NẾU KHÁCH HÀNG "ĐÃ ĐĂNG NHẬP":
                   + Nếu khách ĐÃ nhập Số lượng nhưng CHƯA chọn Size: Phát mã [ASK_SIZE: Mã SP: Size1, Size2 : Số_Lượng_Khách_Chọn] để hệ thống hỏi Size.
                   + Nếu khách ĐÃ nhập Size nhưng CHƯA nhập Số lượng: Phát mã [ASK_QTY: Mã SP: Size_Khách_Chọn] để hệ thống hỏi Số lượng.
                   + Nếu khách CHƯA nhập CẢ Size và Số lượng: Phát mã [ASK_BOTH: Mã SP: Size1, Size2] để hệ thống hỏi cả hai.
                   + Nếu khách ĐÃ nhắc đến đầy đủ CẢ Size VÀ Số lượng: TRỰC TIẾP chèn mã [ADD_CART: Mã_SP : Size : Số_Lượng] ở cuối câu. (Hệ thống sẽ tự nhận dạng, bạn không cần hỏi thêm).
            4. Giao tiếp: nhiệt tình, xưng "mình", gọi "bạn".

            --- DỮ LIỆU SẢN PHẨM ---
            {products_context}
            --- END DỮ LIỆU ---
            """

            # Gọi Groq API
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.75, 
            )
            ai_reply = completion.choices[0].message.content

            cart_match = re.search(r'\[ADD_CART:\s*(\d+)\s*:\s*([^\]:]+)(?:\s*:\s*(\d+))?\]', ai_reply)
            cart = request.session.get('cart', {})
            if not isinstance(cart, dict): cart = {}
            added_to_cart = False

            if cart_match and is_authenticated:
                p_id = cart_match.group(1).strip()
                size = cart_match.group(2).strip()
                qty_str = cart_match.group(3)
                qty = int(qty_str.strip()) if qty_str else 1
                try:
                    product = Product.objects.get(id=p_id)
                    key = f"{p_id}_{size}"
                    if key in cart:
                        cart[key]['quantity'] += qty
                    else:
                        cart[key] = {
                            'product_id': p_id,
                            'name': product.name, 
                            'price': str(product.price), 
                            'quantity': qty, 
                            'size': size
                        }
                    request.session['cart'] = cart
                    request.session.modified = True
                    added_to_cart = True
                    ai_reply = re.sub(r'\[ADD_CART:.*?\]', f'\n\n[Hệ thống: Đã thêm {qty} sản phẩm {product.name} size {size} vào giỏ! 🛍️]', ai_reply)
                except Exception:
                    pass

            cart_count = sum(item.get('quantity', 0) for item in cart.values() if isinstance(item, dict))
            request.session['cart_count'] = cart_count

            # Lưu DB
            if user:
                ChatMessage.objects.create(
                    user=user, 
                    message=clean_text_for_db(ai_reply), 
                    is_bot=True
                )

            return JsonResponse({'response': ai_reply, 'cart_count': cart_count, 'added_to_cart': added_to_cart})

        except Exception as e:
            logger.error(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def get_chat_history(request):
    """Lấy 50 tin nhắn lịch sử gần nhất để chat không bị trôi lên quá xa"""
    if request.user.is_authenticated:
        recent_history = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:50]
        history = list(recent_history)[::-1]
        
        return JsonResponse({
            'history': [{'message': h.message, 'is_bot': h.is_bot} for h in history]
        })
    return JsonResponse({'history': []})


# ==========================================
# 4. TÍCH HỢP CỔNG THANH TOÁN VNPAY ONLINE
# ==========================================

def create_vnpay_payment(request, order_id):
    """Hàm lấy thông tin đơn hàng và tạo link dẫn sang cổng thanh toán VNPay Sandbox"""
    order = get_object_or_404(Order, id=order_id)
    
    vnpay = VNPayService(
        tmn_code=settings.VNP_TMN_CODE,
        hash_secret=settings.VNP_HASH_SECRET,
        payment_url=settings.VNP_URL,
        return_url=settings.VNP_RETURN_URL
    )
    
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    create_date = datetime.now().strftime('%Y%m%d%H%M%S')
    order_desc = f"Thanh toan don hang {order.id} tai Website Shoe Store"
    
    payment_url = vnpay.generate_payment_url(
        order_id=order.id,
        amount=float(order.total_price),  
        order_desc=order_desc,
        ip_address=ip_address,
        create_date=create_date
    )
    
    return redirect(payment_url)


def vnpay_return(request):
    """Hàm xử lý phản hồi dữ liệu sau khi khách thao tác xong bên trang cổng VNPay"""
    response_data = request.GET.dict()
    
    vnpay = VNPayService(
        tmn_code=settings.VNP_TMN_CODE,
        hash_secret=settings.VNP_HASH_SECRET,
        payment_url=settings.VNP_URL,
        return_url=settings.VNP_RETURN_URL
    )
    
    if vnpay.validate_response(response_data):
        order_id = response_data.get('vnp_TxnRef')
        response_code = response_data.get('vnp_ResponseCode')
        
        try:
            order = Order.objects.get(id=order_id)
            
            if response_code == '00':
                order.status = 'Completed'  # Cập nhật cờ thanh toán thành công
                order.save()
                
                # ========================================================
                # 🔥 ĐOẠN CODE "XỊN XÒ": TỰ ĐỘNG GỬI SMS THỜI GIAN THỰC
                # ========================================================
                # Lấy số điện thoại từ Order - an toàn tránh AttributeError
                customer_phone = getattr(order, 'phone', None)
                
                if customer_phone:
                    try:
                        send_sms_notification(
                            phone_number=str(customer_phone).strip(),
                            order_id=order.id,
                            total_price=int(order.total_price)
                        )
                    except Exception as sms_error:
                        logger.error(f"Lỗi gửi SMS cho đơn #{order.id}: {str(sms_error)}")
                # ========================================================
                
                return render(request, 'payment_success.html', {'order': order, 'vnpay_data': response_data})
            else:
                order.status = 'Payment_Failed'  
                order.save()
                return render(request, 'payment_failed.html', {'order': order, 'error_code': response_code})
                
        except Order.DoesNotExist:
            return HttpResponse("Hệ thống không tìm thấy hóa đơn đơn hàng tương ứng.")
    else:
        return HttpResponse("Yêu cầu không hợp lệ! Xác thực chữ ký bảo mật (Checksum) thất bại.")