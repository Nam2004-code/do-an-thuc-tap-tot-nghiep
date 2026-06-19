import hashlib
import hmac
import urllib.parse

class VNPayService:
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
            'vnp_Amount': int(amount * 100),  # VNPay yêu cầu số tiền nhân với 100 (Ví dụ: 10000 VND thành 1000000)
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': str(order_id),
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_Locale': 'vn',
            'vnp_ReturnUrl': self.return_url,
            'vnp_IpAddr': ip_address,
            'vnp_CreateDate': create_date,
        }
        
        # Sắp xếp các tham số theo bảng chữ cái từ A-Z
        sorted_params = sorted(vnp_params.items())
        
        # Tạo chuỗi query dạng key1=value1&key2=value2
        query_string = urllib.parse.urlencode(sorted_params)
        
        # Tạo chữ ký mã hóa bảo mật HMAC-SHA512
        hmac_value = hmac.new(
            self.hash_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Ghép chữ ký vào URL để tạo link hoàn chỉnh
        payment_url = f"{self.payment_url}?{query_string}&vnp_SecureHash={hmac_value}"
        return payment_url

    def validate_response(self, response_data):
        """Hàm kiểm tra tính hợp lệ của dữ liệu phản hồi từ VNPay gửi về"""
        vnp_secure_hash = response_data.get('vnp_SecureHash', '')
        
        # Lọc bỏ tham số Hash ra khỏi danh sách để kiểm tra tính toàn vẹn dữ liệu
        params = {k: v for k, v in response_data.items() if k.startswith('vnp_') and k != 'vnp_SecureHash' and k != 'vnp_SecureHashType'}
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)
        
        # Tính toán lại chữ ký từ dữ liệu nhận được
        calculated_hash = hmac.new(
            self.hash_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return calculated_hash == vnp_secure_hash