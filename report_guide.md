# BÁO CÁO THỰC TẬP / TIỂU LUẬN: CÁC TÍNH NĂNG ĐÃ THỰC HIỆN

Dưới đây là chi tiết các cụm tính năng mà bạn đã phát triển, bao gồm vị trí các file can thiệp và giải thích đoạn code đảm nhận từng chức năng cụ thể để bạn dễ dàng trình bày trước hội đồng/giáo viên.

---

## 1. Trợ lý Ảo Chatbot AI (Tư vấn & Chốt đơn tự động)

Đây là chức năng phức tạp và hiện đại nhất, tích hợp Trí tuệ nhân tạo (Llama 3) vào website thương mại điện tử để tự động nhận diện nhu cầu mua hàng và xử lý vào Giỏ.

### 📍 File Backend: `shoestore/views.py`
*   **Kết nối Llama 3 (Dòng 11 - 27):** Sử dụng thư viện `groq` kết nối qua API Key để gọi giao tiếp đa luồng với model `llama-3.3-70b-versatile` xử lý tư vấn ngôn ngữ cực nhanh.
*   **Hàm `clean_text_for_db(text)`:** Hàm xử lý chuỗi tinh vi phân tích ký tự bằng hàm `ord(c) < 0x10000`, chặn các Emojis gây lỗi cơ sở dữ liệu MySQL mà KHÔNG làm mất phông chữ dấu câu đặc thù của tiếng Việt.
*   **Hàm `get_response(request)` (Logic cốt lõi):**
    *   **Prompt Engineering (Luật AI):** Truyền trạng thái Đăng nhập hệ thống vào bộ não AI. Ép AI đóng vai chuyên gia và trả về 4 "Mật Lệnh" riêng biệt như `[ASK_BOTH]`, `[ASK_SIZE]`, `[ASK_QTY]`, `[ADD_CART]` tùy vào việc người dùng chat thiếu Size hay thiếu Số Lượng.
    *   **Phân tích NLP sang Code:** Dùng biểu thức Regex `re.search(r'\[ADD_CART:\s*(\d+)\s*:\s*([^\]:]+)(?:\s*:\s*(\d+))?\]')` chọc thẳng vào câu trả lời AI trả về để tách chính xác ID Sản phẩm, Size giày, Số lượng mua.
    *   **Tương tác Session Giỏ hàng:** Sau khi tách lệnh, tự động cộng dồn số lượng trực tiếp trong Session Giỏ hàng Server (`request.session['cart']`).

### 📍 File Frontend: `templates/base.html`
*   **Hàm `processChatApi()`:** Gửi kết nối RESTful API (`fetch AJAX`) chứa `apiText` (lệnh gửi cho máy) và `displayText` (để lưu vào lịch sử hiển thị của người).
*   **Javascript UI Decoder (Dòng 290+):** Mã JS bóc tách Mật lệnh từ Server về (như `[ASK_BOTH]`). Nó dùng logic tạo ra hộp thoại HTML `<button>` bấm Size và thẻ input `<input type="number">` để tương tác chốt số lượng cực xịn sò mà không cần trả lời qua text rườm rà.
*   **Reload Giỏ hàng Thông minh:** Khi phát hiện có chốt đơn thành công (`added_to_cart = true`) và khách hàng đang ở trang `Giỏ hàng` (`/cart`), code JS sẽ gắn cờ báo hiệu lưu vào Bộ nhớ tạm (`sessionStorage`) rồi F5 trang ngay lập tức. Sau khi F5, web tự phát hiện cờ nhớ để **bật bung luôn khung Chat ảo** lên giao diện mà không để khách phải ấn tay.

---

## 2. Tìm kiếm & Lọc Sản phẩm tự động (Auto-Filter)

Nâng cấp trải nghiệm người dùng (UX) bằng cách loại bỏ nút "Áp dụng". Bạn chỉ cần chọn lọc, trang web tự động lọc sản phẩm.

### 📍 File Lọc Sản Phẩm: `templates/products/list.html`
*   **Sử dụng EventListener JavaScript (Dòng 209-216):** 
    Khóa khối JS ở cuối file thực hiện bắt vòng lặp chọn tất cả các thẻ `.filter-checkbox`. Mỗi khi hàm kích hoạt Event `change` (Khách nhấp chuột thay đổi ô chọn), nó ép Form tự động Submit ngầm ngay lập tức về Controller.
*   **Ghi nhớ Checkbox bằng URLSearchParams:** Code vận dụng hàm thao tác tham số URL trên thanh địa chỉ giúp trình duyệt tự giữ thanh tích xanh (checked = true) kể cả khi trang web vừa F5 lại.

---

## 3. Quản trị Hồ sơ cá nhân (Edit Profile & Passwords)

Cho phép người dùng quản trị an toàn thông tin Giao hàng, kết hợp cơ chế Pre-fill thông minh.

### 📍 File Database: `users/models.py`
*   **Kế thừa và Mở rộng User:** Bằng việc tạo Class `UserProfile` ánh xạ OneToOne 1-1 với lớp `User` mặc định của Django, hệ thống được mở rộng cấu trúc và bổ sung lưu trữ Số điện thoại (phone) và Địa chỉ cá nhân (address).

### 📍 File Controller: `users/views.py`
*   **Hàm Component `profile_view(request)`:**
    *   *Tính năng Tự Động Học (Pre-fill)*: Đoạn code này chạy Query lệnh tìm kiếm đơn mua gần nhất của khách: `Order.objects.filter(user=request.user)`. Nếu khách có hồ sơ trống, máy chủ lập tức lấy Tên, SĐT, Địa chỉ của đơn hàng đó Gán Mặc Định vào cơ sở Form.
    *   *Mã hóa Bảo mật sửa Mật Khẩu*: Code chạy quy trình xử lý độc lập, bắt buộc khớp hàm `check_password()` mật khẩu cũ. Set mật khẩu mới và triển khai lệnh tối quan trọng `update_session_auth_hash(request, user)` nhằm không cho Token Session của Django bị khựng, **giúp khách không bị văng ra khỏi hệ thống đăng nhập**.

### 📍 File View: `templates/users/profile.html`
*   **Giao diện Form Update (Khoảng 90 Dòng code):** Chuyển dịch thiết kế của phần Cập nhật thông tin và Thay đổi mật khẩu thành hai khối tách biệt rất chuyên nghiệp với nền form sáng (Light-theme), chia hệ thống Cột bằng Bootstrap Grid và bảo mật toàn bộ dữ liệu bằng Django `{% csrf_token %}`.

---

## 4. Quy trình Đổi/Trả hàng trong 7 ngày (Return Policy)

Xây dựng hệ thống cho phép khách hàng tự động yêu cầu đổi trả đối với các đơn hàng đã mua trong vòng 7 ngày gần nhất, với cơ chế lọc thông minh.

### 📍 File Database: `orders/models.py`
*   **Cập nhật Trạng thái & Bổ sung Cấu trúc:** Mở rộng Tuple `STATUS_CHOICES` với các cờ báo hiệu chuyên sâu như `Return_Requested`, `Returned`, `Return_Denied`. Bổ sung trường `return_reason` (Text) để lưu vết lý do trả hàng từ phía người dùng.
*   **Hệ thống Ràng buộc (Property Method) `can_return`:** Xây dựng một hàm ảo property tự động kiểm tra thời gian thực. Đoạn code sử dụng `timezone.now() - self.created_at <= datetime.timedelta(days=7)` kèm theo điều kiện đơn hàng phải mang trạng thái `Completed` (Đã giao hàng) để khóa chặt nghiệp vụ, ngăn chặn khách hàng đổi trả sai quy định hoặc vượt quá số ngày.

### 📍 File Controller: `products/views.py`
*   **Hàm Component `return_eligible_orders(request)`:** Hàm này thực thi truy vấn kết hợp: Tìm kiếm toàn bộ đơn hàng của user, loại trừ các đơn hàng bị Hủy (`exclude('Cancelled')`), nhưng bắt buộc thời gian khởi tạo nằm trong ngưỡng 7 ngày (`created_at__gte`). Việc này giúp người dùng dễ dàng theo dõi tất cả lịch sử mua gần nhất ngay trên một màn hình đổi trả riêng biệt.
*   **Endpoint API Form Gửi Đổi Trả `request_return`:** Tiếp nhận POST request, bắt buộc kiểm tra lại thuộc tính `can_return` (tránh Hacker gửi request ảo bỏ qua Giao diện). Sau đó thay đổi trạng thái sang `Return_Requested` và chèn Lý do của khách hàng vào CSDL để báo cho Admin.

### 📍 File Frontend UI: `templates/return_eligible_orders.html` & `home.html`
*   **Giao diện phân bổ Nút thông minh:** Code HTML/Jinja được phân luồng xử lý: Nếu đơn hàng `Completed`, hiện nút vàng rực "Xem & Đổi trả". Nếu đơn hàng đang vận chuyển/chờ xác nhận, chỉ hiện nút "Xem chi tiết" bằng màu Đen nhạt.
*   **Bootstrap Modal Trải Nghiệm Mượt Mà:** Sử dụng Modal chèn trực tiếp Form điền lý do vào trong màn hình chi tiết, giúp khách không phải nhảy sang trang web khác, duy trì trải nghiệm liền mạch và giữ chân khách hàng (Retention) tốt hơn. Dòng lệnh báo lỗi/thành công cũng được hiển thị dạng Badge đẹp mắt.
