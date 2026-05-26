from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Order, OrderItem
from products.models import Product 
from cart.models import Cart, CartItem 
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)


def _extract_quantity(cart_value):
    if isinstance(cart_value, dict):
        return int(cart_value.get('quantity', 0) or 0)
    return int(cart_value or 0)

@login_required(login_url='login')
def checkout(request):
    # Lấy danh sách key sản phẩm từ URL (ví dụ: ?items=1_40,2_39)
    item_keys_str = request.GET.get('items', '')
    cart = request.session.get('cart', {})
    
    if not item_keys_str:
        messages.error(request, 'Giỏ hàng của bạn đang trống.')
        return redirect('cart:cart_detail')
    
    items_to_display = []
    total_price = 0
    errors = []
    
    for key in item_keys_str.split(','):
        if not key or key not in cart:
            continue
        
        try:
            quantity = _extract_quantity(cart[key])
            if quantity <= 0:
                errors.append(f'Sản phẩm có số lượng không hợp lệ')
                continue
            
            # Tách lấy ID từ key (ví dụ "1_39" -> lấy "1")
            product_id = key.split('_')[0]
            
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                errors.append(f'Sản phẩm không tồn tại')
                continue
            
            if not product.is_active:
                errors.append(f'Sản phẩm {product.name} không còn bán')
                continue
            
            # Kiểm tra kho hàng
            if product.stock <= 0:
                errors.append(f'Sản phẩm {product.name} hiện tại không có hàng')
                continue
            
            if quantity > product.stock:
                errors.append(f'Chỉ còn {product.stock} {product.name} trong kho')
                continue
            
            size = key.split('_')[1] if '_' in key else 'N/A'
            line_total = int(product.price) * quantity
            
            display_item = {
                'item_key': key,
                'product': product,
                'quantity': quantity,
                'size': size,
                'price': product.price,
                'total_price': line_total
            }
            total_price += line_total
            items_to_display.append(display_item)
        
        except (ValueError, IndexError) as e:
            errors.append('Thông tin sản phẩm không hợp lệ')
            continue
    
    if errors:
        for error in errors:
            messages.warning(request, error)
    
    if not items_to_display:
        messages.error(request, 'Không có sản phẩm hợp lệ để thanh toán.')
        return redirect('cart:cart_detail')

    context = {
        'items': items_to_display,
        'total_price': total_price,
    }
    return render(request, 'checkout.html', context)

@login_required(login_url='login')
def order_create(request):
    if request.method == 'POST':
        full_name = (request.POST.get('full_name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        address = (request.POST.get('address') or '').strip()
        payment_method = (request.POST.get('payment_method') or '').strip()
        selected_items = (request.POST.get('selected_items') or '').strip()
        
        # Ưu tiên danh sách item từ POST, fallback về query string để tương thích cũ
        item_keys_str = selected_items or request.GET.get('items', '')
        cart_session = request.session.get('cart', {})
        
        # Validation for empty items
        if not item_keys_str:
            messages.error(request, "Vui lòng chọn ít nhất một sản phẩm để đặt hàng.")
            return redirect('cart:cart_detail')

        # Validation for full name
        if not full_name:
            messages.error(request, 'Vui lòng cung cấp họ và tên.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')
        
        if len(full_name) > 200:
            messages.error(request, 'Họ và tên quá dài (tối đa 200 ký tự).')
            return redirect(f'/orders/checkout/?items={item_keys_str}')

        # Validation for phone
        if not phone:
            messages.error(request, 'Vui lòng cung cấp số điện thoại.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')
        
        if not phone.isdigit():
            messages.error(request, 'Số điện thoại chỉ được chứa các chữ số.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')
        
        if len(phone) < 9 or len(phone) > 11:
            messages.error(request, 'Số điện thoại không hợp lệ (9-11 chữ số).')
            return redirect(f'/orders/checkout/?items={item_keys_str}')

        # Validation for address
        if not address:
            messages.error(request, 'Vui lòng cung cấp địa chỉ giao hàng.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')
        
        if len(address) > 1000:
            messages.error(request, 'Địa chỉ quá dài (tối đa 1000 ký tự).')
            return redirect(f'/orders/checkout/?items={item_keys_str}')

        # Validation for payment method
        allowed_payment_methods = {'COD', 'BANK'}
        if not payment_method:
            messages.error(request, 'Vui lòng chọn phương thức thanh toán.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')
        
        if payment_method not in allowed_payment_methods:
            messages.error(request, 'Phương thức thanh toán không hợp lệ.')
            return redirect(f'/orders/checkout/?items={item_keys_str}')

        # 1. Tạo đơn hàng
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name, 
            phone=phone, 
            address=address,
            payment_method=payment_method, 
            total_price=0 
        )
        
        current_total = 0
        keys_to_delete = []
        validation_errors = []
        
        for key in item_keys_str.split(','):
            if not key:
                continue
            
            if key not in cart_session:
                validation_errors.append(f'Sản phẩm không có trong giỏ hàng')
                continue
            
            try:
                quantity = _extract_quantity(cart_session[key])
                if quantity <= 0:
                    validation_errors.append(f'Số lượng sản phẩm không hợp lệ')
                    continue
                
                product_id = key.split('_')[0]
                size = key.split('_')[1] if '_' in key else 'N/A'
                
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    validation_errors.append(f'Sản phẩm không tồn tại')
                    continue
                
                if not product.is_active:
                    validation_errors.append(f'Sản phẩm {product.name} không còn bán')
                    continue
                
                # Kiểm tra kho hàng
                if product.stock <= 0:
                    validation_errors.append(f'Sản phẩm {product.name} hiện tại không có hàng')
                    continue
                
                if quantity > product.stock:
                    validation_errors.append(f'Chỉ còn {product.stock} {product.name} trong kho')
                    continue
                
                line_total = int(product.price) * quantity
                current_total += line_total
                
                OrderItem.objects.create(
                    order=order, 
                    product=product,
                    price=product.price,
                    quantity=quantity,
                    size=size
                )
                keys_to_delete.append(key)
            
            except (ValueError, IndexError) as e:
                validation_errors.append(f'Thông tin sản phẩm không hợp lệ')
                continue

        # Nếu không có items hợp lệ, xóa order
        if not keys_to_delete:
            order.delete()
            for error in validation_errors:
                messages.error(request, error)
            if not validation_errors:
                messages.error(request, 'Không có sản phẩm nào hợp lệ để đặt hàng.')
            return redirect('cart:cart_detail')

        order.total_price = current_total
        order.save()
        
        # --- ĐOẠN RESET GIỎ HÀNG VÀ CẬP NHẬT SỐ LƯỢNG ---
        
        # A. Xóa các item đã mua trong Session
        for key in keys_to_delete:
            if key in cart_session:
                del cart_session[key]
        
        # B. CẬP NHẬT LẠI CON SỐ TRÊN HEADER (Dòng quan trọng nhất)
        # Tính tổng số lượng của những sản phẩm CÒN LẠI trong giỏ
        request.session['cart'] = cart_session
        request.session['cart_count'] = sum(_extract_quantity(v) for v in cart_session.values()) if cart_session else 0
        request.session.modified = True

        # C. Xóa trong Database (Sử dụng ID để né lỗi cấu trúc bảng)
        if request.user.is_authenticated:
            try:
                cart_obj = Cart.objects.filter(user=request.user).first()
                if cart_obj:
                    # Chỉ xóa những item mà user vừa đặt hàng thành công trong DB
                    # Hoặc xóa hết item của user đó trong DB cho sạch
                    CartItem.objects.filter(cart=cart_obj).delete()
            except Exception as e:
                logger.warning("Lỗi DB khi xóa cart items sau khi tạo đơn: %s", e)
        
        # Hiển thị warning nếu có lỗi partial
        for error in validation_errors:
            messages.warning(request, error)
        
        # Show success message
        if len(keys_to_delete) > 0:
            messages.success(request, f'Đơn hàng được tạo thành công với {len(keys_to_delete)} sản phẩm!')
        
        # ----------------------------------------------
        
        request.session['last_order_id'] = order.id
        return redirect('orders:order_success')
    
    return redirect('orders:checkout')

@login_required(login_url='login')
def order_success(request):
    # 1. Sửa lại tên key cho khớp với hàm order_create (last_order_id)
    order_id = request.session.get('last_order_id')
    
    order = None
    if order_id:
        order = Order.objects.filter(id=order_id).first()
    
    # 2. Nếu không thấy trong session, lấy đơn mới nhất của chính User đó
    if not order:
        if request.user.is_authenticated:
            order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        else:
            order = Order.objects.order_by('-created_at').first()

    if not order:
        return redirect('products:product_list')

    # 3. Trả về template (Đảm bảo file order_success.html của bạn có đoạn Script tự F5)
    return render(request, 'order_success.html', {'order': order})