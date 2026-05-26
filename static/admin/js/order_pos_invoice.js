(function () {
  // Script hỗ trợ hành vi POS trong Django admin (Order inline):
  // - Tự load giá và size khi chọn product
  // - Tính tổng tạm (preview) cho admin
  // Các hàm được viết ngắn gọn, an toàn với dữ liệu không hợp lệ.
  var bindTimer = null;

  function formatNumber(value) {
    try {
      return Number(value || 0).toLocaleString('vi-VN');
    } catch (e) {
      return String(value || 0);
    }
  }

  function parseNumber(value) {
    if (value === null || value === undefined) return 0;
    var normalized = String(value).replace(/[^0-9.-]/g, '');
    var parsed = parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function getInput(row, suffix) {
    return row.querySelector('input[name$="-' + suffix + '"]') || row.querySelector('select[name$="-' + suffix + '"]');
  }

  function getInlineRows() {
    return Array.prototype.slice.call(document.querySelectorAll('#orderitem_set-group .dynamic-orderitem_set'));
  }

  function ensureTotalPreview() {
    var group = document.getElementById('orderitem_set-group');
    if (!group) return null;

    var box = document.getElementById('pos-order-total-preview');
    if (box) return box;

    box = document.createElement('div');
    box.id = 'pos-order-total-preview';
    box.style.marginTop = '12px';
    box.style.padding = '10px 14px';
    box.style.border = '1px solid #ddd';
    box.style.borderRadius = '8px';
    box.style.background = '#fff';
    box.style.fontWeight = '700';
    box.style.fontSize = '16px';
    box.textContent = 'Tong tien tam tinh: 0 đ';

    group.appendChild(box);
    return box;
  }

  function updateTotal() {
    var rows = getInlineRows();
    var total = 0;

    rows.forEach(function (row) {
      var deleteInput = row.querySelector('input[name$="-DELETE"]');
      if (deleteInput && deleteInput.checked) return;

      var priceInput = getInput(row, 'price');
      var qtyInput = getInput(row, 'quantity');
      var price = parseNumber(priceInput ? priceInput.value : 0);
      var qty = parseNumber(qtyInput ? qtyInput.value : 0);
      total += price * qty;
    });

    var totalInput = document.getElementById('id_total_price');
    if (totalInput) {
      totalInput.value = Math.round(total);
    }

    var preview = ensureTotalPreview();
    if (preview) {
      preview.textContent = 'Tong tien tam tinh: ' + formatNumber(Math.round(total)) + ' đ';
    }
  }

  function updateSizeOptions(sizeSelect, sizes, selectedValue) {
    if (!sizeSelect) return;

    var current = selectedValue || sizeSelect.value;
    sizeSelect.innerHTML = '';

    if (!sizes || !sizes.length) {
      var emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'Khong co size';
      sizeSelect.appendChild(emptyOpt);
      return;
    }

    sizes.forEach(function (sizeValue) {
      var opt = document.createElement('option');
      opt.value = sizeValue;
      opt.textContent = sizeValue;
      if (String(sizeValue) === String(current)) {
        opt.selected = true;
      }
      sizeSelect.appendChild(opt);
    });
  }

  function bindRow(row) {
    if (!row || row.dataset.posBound === '1') return;
    row.dataset.posBound = '1';

    var productSelect = getInput(row, 'product');
    var priceInput = getInput(row, 'price');
    var qtyInput = getInput(row, 'quantity');
    var sizeSelect = getInput(row, 'size');
    var deleteInput = row.querySelector('input[name$="-DELETE"]');

    function refreshByProduct() {
      if (!productSelect || !productSelect.value) {
        row.dataset.lastProductId = '';
        if (priceInput) priceInput.value = '';
        updateSizeOptions(sizeSelect, [], '');
        updateTotal();
        return;
      }

      if (row.dataset.lastProductId === String(productSelect.value)) {
        return;
      }

      row.dataset.lastProductId = String(productSelect.value);

      var url = '/admin/orders/order/product-meta/' + productSelect.value + '/';
      fetch(url, { credentials: 'same-origin' })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!data || !data.success) return;
          if (priceInput) priceInput.value = data.price;
          updateSizeOptions(sizeSelect, data.sizes || [], sizeSelect ? sizeSelect.value : '');
          updateTotal();
        })
        .catch(function () {
          updateTotal();
        });
    }

    if (productSelect) {
      productSelect.addEventListener('change', refreshByProduct);
      // Trigger once so first selected product auto-loads price/size.
      if (productSelect.value) {
        setTimeout(refreshByProduct, 0);
      }
    }

    if (qtyInput) qtyInput.addEventListener('input', updateTotal);
    if (priceInput) priceInput.addEventListener('input', updateTotal);
    if (sizeSelect) sizeSelect.addEventListener('change', updateTotal);
    if (deleteInput) deleteInput.addEventListener('change', updateTotal);
  }

  function bindAllRows() {
    getInlineRows().forEach(bindRow);
    updateTotal();
  }

  function scheduleBindAllRows() {
    if (bindTimer) {
      clearTimeout(bindTimer);
    }
    bindTimer = setTimeout(function () {
      bindAllRows();
      bindTimer = null;
    }, 60);
  }

  document.addEventListener('DOMContentLoaded', function () {
    bindAllRows();

    var addButton = document.querySelector('#orderitem_set-group .add-row a');
    if (addButton) {
      addButton.addEventListener('click', function () {
        scheduleBindAllRows();
      });
    }

    // Django admin emits this event after adding inline rows.
    if (window.django && window.django.jQuery) {
      window.django.jQuery(document).on('formset:added', function () {
        scheduleBindAllRows();
      });
    }
  });
})();
