/**
 * AutoParts CRM — Main JavaScript
 * Handles sidebar toggle, messages, animations, order creation, counters
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initMessages();
    initAnimations();
    initCounters();
    initOrderCreation();
    initProductSearch();
});

/* ═══════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════ */
function initSidebar() {
    const hamburger = document.getElementById('hamburger-btn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (hamburger && sidebar) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('show');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
        });
    }

    // Close sidebar on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            if (overlay) overlay.classList.remove('show');
        }
    });
}

/* ═══════════════════════════════════════════
   MESSAGES
   ═══════════════════════════════════════════ */
function initMessages() {
    const messages = document.querySelectorAll('.message');
    messages.forEach((msg) => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(40px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);

        // Click to dismiss
        msg.addEventListener('click', () => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(40px)';
            setTimeout(() => msg.remove(), 300);
        });
    });
}

/* ═══════════════════════════════════════════
   ANIMATIONS (IntersectionObserver)
   ═══════════════════════════════════════════ */
function initAnimations() {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.1 }
    );

    document.querySelectorAll('.stat-card, .card, .quick-action').forEach((el) => {
        observer.observe(el);
    });
}

/* ═══════════════════════════════════════════
   COUNTER ANIMATION
   ═══════════════════════════════════════════ */
function initCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    counters.forEach((el) => {
        const target = parseInt(el.getAttribute('data-counter'), 10);
        if (isNaN(target)) return;

        const duration = 1500;
        const step = target / (duration / 16);
        let current = 0;

        const update = () => {
            current += step;
            if (current >= target) {
                el.textContent = formatNumber(target);
                return;
            }
            el.textContent = formatNumber(Math.floor(current));
            requestAnimationFrame(update);
        };
        requestAnimationFrame(update);
    });
}

function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

/* ═══════════════════════════════════════════
   ORDER CREATION
   ═══════════════════════════════════════════ */
let orderItems = [];

function initOrderCreation() {
    const addBtn = document.getElementById('add-item-btn');
    if (!addBtn) return;

    addBtn.addEventListener('click', () => {
        addOrderItem();
    });

    // Initialize form submission
    const form = document.getElementById('order-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            const itemsInput = document.getElementById('items-json');
            if (itemsInput) {
                itemsInput.value = JSON.stringify(orderItems);
            }
        });
    }
}

function addOrderItem(productData) {
    const container = document.getElementById('order-items-container');
    if (!container) return;

    const index = orderItems.length;
    const item = productData || {
        product_id: '',
        product_name: '',
        quantity: 1,
        price: 0,
    };

    orderItems.push(item);

    const row = document.createElement('div');
    row.className = 'order-item-row';
    row.dataset.index = index;
    row.innerHTML = `
        <div class="product-search-wrapper">
            <input type="text" class="form-input product-search-input"
                   placeholder="Поиск по OEM / названию..."
                   value="${item.product_name}"
                   data-index="${index}"
                   autocomplete="off">
            <input type="hidden" class="product-id-input" value="${item.product_id}">
            <div class="product-dropdown" id="dropdown-${index}"></div>
        </div>
        <input type="number" class="form-input item-qty" value="${item.quantity}"
               min="1" data-index="${index}" placeholder="Кол-во">
        <input type="number" class="form-input item-price" value="${item.price}"
               min="0" step="0.01" data-index="${index}" placeholder="Цена">
        <span class="item-total" data-index="${index}">0 ₸</span>
        <button type="button" class="remove-item-btn" onclick="removeOrderItem(${index})">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;

    container.appendChild(row);
    initItemEvents(row, index);
    updateOrderTotal();
}

function initItemEvents(row, index) {
    const searchInput = row.querySelector('.product-search-input');
    const qtyInput = row.querySelector('.item-qty');
    const priceInput = row.querySelector('.item-price');

    // Product search
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        if (query.length < 2) {
            hideDropdown(index);
            return;
        }
        searchTimeout = setTimeout(() => {
            searchProducts(query, index);
        }, 300);
    });

    searchInput.addEventListener('blur', () => {
        setTimeout(() => hideDropdown(index), 200);
    });

    // Quantity / Price changes
    qtyInput.addEventListener('input', () => {
        orderItems[index].quantity = parseInt(qtyInput.value) || 0;
        updateItemTotal(index);
    });

    priceInput.addEventListener('input', () => {
        orderItems[index].price = parseFloat(priceInput.value) || 0;
        updateItemTotal(index);
    });
}

function searchProducts(query, index) {
    fetch(`/orders/api/products/?q=${encodeURIComponent(query)}`)
        .then((r) => r.json())
        .then((data) => {
            const dropdown = document.getElementById(`dropdown-${index}`);
            if (!dropdown) return;

            if (data.results.length === 0) {
                dropdown.innerHTML = '<div class="product-dropdown-item"><span class="text-muted">Ничего не найдено</span></div>';
            } else {
                dropdown.innerHTML = data.results
                    .map(
                        (p) => `
                    <div class="product-dropdown-item" onclick="selectProduct(${index}, ${p.id}, '${escapeHtml(p.name)}', ${p.price_retail}, ${p.stock_quantity})">
                        <div>
                            <div class="product-dropdown-name">${escapeHtml(p.name)}</div>
                            <div class="product-dropdown-oem">${p.oem_number} ${p.part_number ? '/ ' + p.part_number : ''}</div>
                        </div>
                        <div class="text-right">
                            <div class="product-dropdown-price">${parseFloat(p.price_retail).toLocaleString()} ₸</div>
                            <div class="product-dropdown-stock">Остаток: ${p.stock_quantity}</div>
                        </div>
                    </div>
                `
                    )
                    .join('');
            }
            dropdown.classList.add('show');
        })
        .catch(() => {
            hideDropdown(index);
        });
}

function selectProduct(index, productId, name, price, stock) {
    const row = document.querySelector(`.order-item-row[data-index="${index}"]`);
    if (!row) return;

    row.querySelector('.product-search-input').value = name;
    row.querySelector('.product-id-input').value = productId;
    row.querySelector('.item-price').value = price;

    orderItems[index] = {
        product_id: productId,
        product_name: name,
        quantity: parseInt(row.querySelector('.item-qty').value) || 1,
        price: price,
    };

    hideDropdown(index);
    updateItemTotal(index);
}

function removeOrderItem(index) {
    const row = document.querySelector(`.order-item-row[data-index="${index}"]`);
    if (row) row.remove();
    orderItems[index] = null;
    updateOrderTotal();
}

function hideDropdown(index) {
    const dropdown = document.getElementById(`dropdown-${index}`);
    if (dropdown) dropdown.classList.remove('show');
}

function updateItemTotal(index) {
    const item = orderItems[index];
    if (!item) return;

    const total = item.quantity * item.price;
    const totalEl = document.querySelector(`.item-total[data-index="${index}"]`);
    if (totalEl) {
        totalEl.textContent = total.toLocaleString() + ' ₸';
    }
    updateOrderTotal();
}

function updateOrderTotal() {
    let total = 0;
    orderItems.forEach((item) => {
        if (item) total += item.quantity * item.price;
    });

    const totalEl = document.getElementById('order-grand-total');
    if (totalEl) {
        totalEl.textContent = total.toLocaleString() + ' ₸';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, "\\'");
}

/* ═══════════════════════════════════════════
   GLOBAL PRODUCT SEARCH (catalog page)
   ═══════════════════════════════════════════ */
function initProductSearch() {
    const searchForm = document.getElementById('search-form');
    if (!searchForm) return;

    const inputs = searchForm.querySelectorAll('select');
    inputs.forEach((input) => {
        input.addEventListener('change', () => {
            searchForm.submit();
        });
    });
}

/* ═══════════════════════════════════════════
   STOCK ADJUSTMENT MODAL
   ═══════════════════════════════════════════ */
function openStockModal(productId, productName, currentQty) {
    const modal = document.getElementById('stock-modal');
    if (!modal) return;

    document.getElementById('modal-product-name').textContent = productName;
    document.getElementById('modal-product-id').value = productId;
    document.getElementById('modal-quantity').value = currentQty;
    document.getElementById('stock-adjust-form').action = `/warehouse/adjust/${productId}/`;

    modal.style.display = 'flex';
}

function closeStockModal() {
    const modal = document.getElementById('stock-modal');
    if (modal) modal.style.display = 'none';
}

/* ═══════════════════════════════════════════
   NAVBAR BLUR ON SCROLL
   ═══════════════════════════════════════════ */
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    if (window.scrollY > 10) {
        navbar.style.background = 'rgba(8, 8, 15, 0.95)';
        navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
    } else {
        navbar.style.background = 'rgba(8, 8, 15, 0.85)';
        navbar.style.boxShadow = 'none';
    }
});

/* ═══════════════════════════════════════════
   REPORT PERIOD SWITCH
   ═══════════════════════════════════════════ */
function setPeriod(days) {
    const url = new URL(window.location.href);
    url.searchParams.set('period', days);
    url.searchParams.delete('date_from');
    url.searchParams.delete('date_to');
    window.location.href = url.toString();
}
