from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from products.models import Product
from django.contrib.humanize.templatetags.humanize import intcomma
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
import json

"""Views xử lý giỏ hàng và API liên quan.

Bao gồm các view HTML (cart_detail, add_to_cart, update_cart, remove_from_cart, checkout)
và API JSON tương ứng (`api_*`).
"""


# Hàm phụ trợ xử lý cả 2 loại dữ liệu (int của web và dict của chatbot)
def _get_cart_data(cart):
    total = 0
    for item_key, item_val in cart.items():
        # Trích xuất đúng số lượng bất kể là int hay dict
        quantity = item_val['quantity'] if isinstance(item_val, dict) else item_val
        try:
            p_id = item_key.split('_')[0]
            product = Product.objects.get(id=int(p_id))
            total += product.price * quantity
        except:
            continue
    return total

def cart_detail(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    product_ids_in_cart = [] # Danh sách ID để loại trừ sản phẩm đã có trong giỏ

    for item_key, item_val in cart.items():
        quantity = item_val['quantity'] if isinstance(item_val, dict) else item_val
        try:
            parts = item_key.split('_')
            p_id = parts[0]
            product_ids_in_cart.append(int(p_id)) # Thêm ID vào danh sách loại trừ
            
            size = parts[1] if len(parts) > 1 else "N/A"
            product = Product.objects.get(id=int(p_id))
            item_total = product.price * quantity
            total += item_total
            items.append({
                'product': product,
                'quantity': quantity,
                'size': size,
                'item_key': item_key,
                'total_price': item_total,
            })
        except (Product.DoesNotExist, ValueError, IndexError):
            continue 

    # --- PHẦN GỢI Ý SẢN PHẨM (SỬA Ở ĐÂY) ---
    # Lấy 4 sản phẩm ngẫu nhiên không có trong giỏ hàng
    recommended_products = Product.objects.exclude(id__in=product_ids_in_cart).order_by('?')[:4]
    
    # Nếu không còn sản phẩm nào để loại trừ, lấy 4 sản phẩm bất kỳ
    if not recommended_products.exists():
        recommended_products = Product.objects.all()[:4]
    # ---------------------------------------

    return render(request, 'cart.html', {
        'items': items, 
        'total': total,
        'recommended_products': recommended_products # Truyền biến này ra template
    })

def add_to_cart(request, product_id):
    if request.method == 'POST':
        # Enforce authentication: require login to add to cart
        if not request.user.is_authenticated:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'Bạn cần đăng nhập để thêm vào giỏ hàng',
                    'error_code': 'login_required'
                }, status=401)
            # redirect to login page with next back to product
            return HttpResponseRedirect(f"/accounts/login/?next={request.path}")
        
        # Kiểm tra sản phẩm tồn tại
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Sản phẩm không tồn tại hoặc đã bị xóa',
                    'error_code': 'product_not_found'
                }, status=404)
            return redirect('home')
        
        # Lấy số lượng và kiểm tra hợp lệ
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Số lượng không hợp lệ',
                    'error_code': 'invalid_quantity'
                }, status=400)
            quantity = 1
        
        # Validate quantity
        if quantity < 1:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Số lượng phải lớn hơn 0',
                    'error_code': 'quantity_too_low'
                }, status=400)
            quantity = 1
        
        if quantity > 999:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Số lượng không được vượt quá 999',
                    'error_code': 'quantity_too_high'
                }, status=400)
            quantity = 999
        
        # Kiểm tra kho hàng
        if product.stock <= 0:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Sản phẩm này hiện tại không có hàng',
                    'error_code': 'out_of_stock'
                }, status=400)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'error': 'out_of_stock'}, status=400)
        
        if quantity > product.stock:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'Chỉ còn {product.stock} sản phẩm trong kho',
                    'error_code': 'insufficient_stock'
                }, status=400)
        
        size = request.POST.get('size', 'N/A')
        item_key = f"{product_id}_{size}"
        
        cart = request.session.get('cart', {})
        
        # Tương thích cộng dồn cho cả 2 kiểu dữ liệu
        if item_key in cart:
            if isinstance(cart[item_key], dict):
                cart[item_key]['quantity'] += quantity
            else:
                cart[item_key] += quantity
        else:
            cart[item_key] = quantity
        
        request.session['cart'] = cart
        # Tính tổng số lượng hiển thị trên icon
        new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
        request.session['cart_count'] = new_count
        request.session.modified = True
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'cart_count': new_count,
                'message': f'Đã thêm {product.name} vào giỏ hàng'
            })
        return redirect('cart:cart_detail')
    return redirect('home')

def update_cart(request, item_key=None, action=None):
    item_key = item_key or request.GET.get('item_key') or request.POST.get('item_key')
    action = action or request.GET.get('action') or request.POST.get('action')

    if not item_key or not action:
        return JsonResponse({
            'success': False, 
            'error': 'Thông tin không hợp lệ',
            'error_code': 'missing_params'
        }, status=400)

    if action not in ['increase', 'decrease']:
        return JsonResponse({
            'success': False,
            'error': 'Hành động không hợp lệ',
            'error_code': 'invalid_action'
        }, status=400)

    cart = request.session.get('cart', {})
    item_total_html = "0"
    current_qty = 0
    
    if item_key not in cart:
        return JsonResponse({
            'success': False,
            'error': 'Sản phẩm không có trong giỏ hàng',
            'error_code': 'item_not_found'
        }, status=404)
    
    try:
        is_dict = isinstance(cart[item_key], dict)
        current_qty = cart[item_key]['quantity'] if is_dict else cart[item_key]
        
        if action == 'increase':
            current_qty += 1
        elif action == 'decrease':
            current_qty -= 1
        
        # Validate stock before increase
        if action == 'increase':
            p_id = item_key.split('_')[0]
            product = Product.objects.get(id=int(p_id))
            if current_qty > product.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Chỉ còn {product.stock} sản phẩm trong kho',
                    'error_code': 'insufficient_stock'
                }, status=400)
        
        if current_qty <= 0:
            del cart[item_key]
            current_qty = 0
        else:
            if is_dict:
                cart[item_key]['quantity'] = current_qty
            else:
                cart[item_key] = current_qty
        
        if item_key in cart:
            p_id = item_key.split('_')[0]
            product = Product.objects.get(id=int(p_id))
            item_total_html = intcomma(product.price * current_qty)

        request.session['cart'] = cart
        new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
        request.session['cart_count'] = new_count
        request.session.modified = True
        
        new_total_cart = _get_cart_data(cart)
        
        return JsonResponse({
            'success': True, 
            'cart_count': new_count,
            'item_count': current_qty if item_key in cart else 0,
            'item_total': item_total_html,
            'total_cart': intcomma(new_total_cart)
        })
    
    except (Product.DoesNotExist, ValueError, KeyError) as e:
        return JsonResponse({
            'success': False,
            'error': 'Có lỗi xảy ra khi cập nhật giỏ hàng',
            'error_code': 'update_error'
        }, status=500)

def remove_from_cart(request, item_key=None):
    item_key = item_key or request.GET.get('item_key') or request.POST.get('item_key')
    if not item_key:
        return JsonResponse({
            'success': False, 
            'error': 'Thông tin không hợp lệ',
            'error_code': 'missing_item_key'
        }, status=400)

    cart = request.session.get('cart', {})
    
    if item_key not in cart:
        return JsonResponse({
            'success': False,
            'error': 'Sản phẩm không có trong giỏ hàng',
            'error_code': 'item_not_found'
        }, status=404)
    
    try:
        del cart[item_key]
        
        request.session['cart'] = cart
        new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
        request.session['cart_count'] = new_count
        request.session.modified = True
        
        new_total_cart = _get_cart_data(cart)
        
        return JsonResponse({
            'success': True,
            'cart_count': new_count,
            'total_cart': intcomma(new_total_cart),
            'message': 'Đã xóa sản phẩm khỏi giỏ hàng'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Có lỗi xảy ra khi xóa sản phẩm',
            'error_code': 'delete_error'
        }, status=500)

def checkout(request):
    item_keys_str = request.GET.get('items', '')
    if not item_keys_str:
        return redirect('cart:cart_detail')
    return redirect(f"/orders/checkout/?items={item_keys_str}")


# -------------------- API wrapper views --------------------
@csrf_exempt
@require_http_methods(["GET"])
def api_get_cart(request):
    cart = request.session.get('cart', {})
    items = []
    for item_key, item_val in cart.items():
        quantity = item_val['quantity'] if isinstance(item_val, dict) else item_val
        try:
            parts = item_key.split('_')
            p_id = parts[0]
            size = parts[1] if len(parts) > 1 else "N/A"
            product = Product.objects.get(id=int(p_id))
            items.append({
                'item_key': item_key,
                'product_id': product.id,
                'name': getattr(product, 'name', str(product)),
                'price': float(product.price),
                'quantity': quantity,
                'size': size,
            })
        except Exception:
            continue

    total = _get_cart_data(cart)
    cart_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
    return JsonResponse({'items': items, 'total': float(total), 'cart_count': cart_count})


@csrf_exempt
@require_http_methods(["POST"])
def api_add_to_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    product_id = data.get('product_id') or request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'success': False, 'error': 'product_id required'}, status=400)

    try:
        quantity = int(data.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    size = data.get('size', 'N/A')

    # Enforce authentication for API add-to-cart as well
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'login_required'}, status=401)

    cart = request.session.get('cart', {})
    item_key = f"{product_id}_{size}"

    if item_key in cart:
        if isinstance(cart[item_key], dict):
            cart[item_key]['quantity'] += quantity
        else:
            cart[item_key] += quantity
    else:
        cart[item_key] = quantity

    request.session['cart'] = cart
    new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
    request.session['cart_count'] = new_count
    request.session.modified = True

    return JsonResponse({'success': True, 'cart_count': new_count})


@csrf_exempt
@require_http_methods(["POST"])
def api_update_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    item_key = data.get('item_key') or request.POST.get('item_key')
    action = data.get('action') or request.POST.get('action')
    quantity = data.get('quantity')

    if not item_key:
        return JsonResponse({'success': False, 'error': 'item_key required'}, status=400)

    cart = request.session.get('cart', {})
    if item_key not in cart:
        return JsonResponse({'success': False, 'error': 'item not found'}, status=404)

    is_dict = isinstance(cart[item_key], dict)
    current_qty = cart[item_key]['quantity'] if is_dict else cart[item_key]

    if quantity is not None:
        try:
            current_qty = int(quantity)
        except (ValueError, TypeError):
            pass
    elif action == 'increase':
        current_qty += 1
    elif action == 'decrease':
        current_qty -= 1

    if current_qty <= 0:
        del cart[item_key]
        current_qty = 0
    else:
        if is_dict:
            cart[item_key]['quantity'] = current_qty
        else:
            cart[item_key] = current_qty

    request.session['cart'] = cart
    new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
    request.session['cart_count'] = new_count
    request.session.modified = True

    new_total_cart = _get_cart_data(cart)

    return JsonResponse({
        'success': True,
        'cart_count': new_count,
        'item_count': current_qty,
        'total_cart': float(new_total_cart)
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_remove_from_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    item_key = data.get('item_key') or request.POST.get('item_key')
    if not item_key:
        return JsonResponse({'success': False, 'error': 'item_key required'}, status=400)

    cart = request.session.get('cart', {})
    if item_key in cart:
        del cart[item_key]

    request.session['cart'] = cart
    new_count = sum(v['quantity'] if isinstance(v, dict) else v for v in cart.values())
    request.session['cart_count'] = new_count
    request.session.modified = True

    new_total_cart = _get_cart_data(cart)

    return JsonResponse({'success': True, 'cart_count': new_count, 'total_cart': float(new_total_cart)})


@csrf_exempt
@require_http_methods(["POST"])
def api_checkout(request):
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    item_keys = data.get('items') or []
    if not item_keys:
        return JsonResponse({'success': False, 'error': 'no items provided'}, status=400)

    cart = request.session.get('cart', {})
    checkout_items = []
    total_price = 0

    for key in item_keys:
        if key in cart:
            try:
                parts = key.split('_')
                product_id = parts[0]
                size = parts[1] if len(parts) > 1 else 'N/A'
                quantity = cart[key]['quantity'] if isinstance(cart[key], dict) else cart[key]
                product = Product.objects.get(id=int(product_id))
                item_total = float(product.price) * int(quantity)
                total_price += item_total
                checkout_items.append({'item_key': key, 'product_id': product.id, 'quantity': quantity, 'size': size, 'total_price': item_total})
            except Exception:
                continue

    return JsonResponse({'success': True, 'items': checkout_items, 'total_price': float(total_price)})