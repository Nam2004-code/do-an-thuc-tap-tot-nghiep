import requests
from django.conf import settings

def send_sms_notification(phone_number, order_id, total_price):
    """
    Hàm kết nối với API SpeedSMS để gửi tin nhắn thông báo đơn hàng thành công
    """
    url = "https://api.speedsms.vn/index.php/sms/send"
    
    # Định dạng lại số điện thoại về chuẩn 84 (nếu cần, ví dụ 09123... thành 849123...)
    if phone_number.startswith('0'):
        phone_number = '84' + phone_number[1:]
        
    # Nội dung tin nhắn (Tùy thuộc vào gói SMS bạn đăng ký, thường là SMS chăm sóc khách hàng)
    content = f"Cảm ơn bạn đã mua hàng tại Shoes Store. Đơn hàng #{order_id} trị giá {total_price}đ đã được tạo thành công và đang được xử lý."
    
    # Tham số truyền lên API của bên thứ ba
    payload = {
        'to': phone_number,
        'content': content,
        'sms_type': 2, # 2 là loại SMS Chăm sóc khách hàng (CSKH)
        'sender': settings.SPEEDSMS_SENDER
    }
    
    # Gọi API bằng phương thức Basic Authentication theo tài liệu của SpeedSMS
    try:
        response = requests.post(
            url, 
            json=payload, 
            auth=(settings.SPEEDSMS_API_KEY, 'x')
        )
        result = response.json()
        
        # Kiểm tra trạng thái phản hồi từ bên thứ 3
        if result.get('status') == 'success':
            print(f"--> Gửi SMS thành công cho đơn hàng #{order_id}")
            return True
        else:
            print(f"--> Lỗi gửi SMS từ nhà cung cấp: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"--> Không thể kết nối tới API SMS: {str(e)}")
        return False