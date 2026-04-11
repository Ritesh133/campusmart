/* ═══════════════════════════════════════
   CampusMart — Main JavaScript
   ═══════════════════════════════════════ */

/* ──────── Theme Toggle ──────── */
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('cm_theme', next);
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
}

// Restore theme on load
(function() {
  const saved = localStorage.getItem('cm_theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
  }
  
  // Intercept Supabase Auth Recovery hash from email link
  if (window.location.hash.includes('type=recovery') && !window.location.pathname.includes('/accounts/update-password/')) {
    window.location.href = '/accounts/update-password/' + window.location.hash;
  }
})();


/* ──────── Toast Notifications ──────── */
function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3500);
}


/* ──────── User Dropdown Menu ──────── */
function toggleUserMenu() {
  const menu = document.getElementById('user-menu');
  if (!menu) return;
  menu.classList.toggle('active');
}

// Close dropdown on outside click
document.addEventListener('click', function(e) {
  const menu = document.getElementById('user-menu');
  const avatar = document.querySelector('.nav-avatar');
  if (menu && avatar && !menu.contains(e.target) && !avatar.contains(e.target)) {
    menu.classList.remove('active');
  }
  // Close mobile drawer on outside click
  const drawer = document.getElementById('mobile-drawer');
  const hamburger = document.querySelector('.nav-hamburger');
  if (drawer && drawer.classList.contains('open') &&
      !drawer.contains(e.target) && hamburger && !hamburger.contains(e.target)) {
    drawer.classList.remove('open');
    hamburger.classList.remove('open');
  }
});


/* ──────── Mobile Menu Drawer ──────── */
function toggleMobileMenu() {
  const drawer = document.getElementById('mobile-drawer');
  const btn = document.querySelector('.nav-hamburger');
  if (!drawer) return;
  drawer.classList.toggle('open');
  if (btn) btn.classList.toggle('open');
}


/* ──────── Wishlist Toggle (AJAX) ──────── */
function toggleWishlist(listingId, btn) {
  const csrfToken = getCsrfToken();
  fetch(`/api/wishlist/${listingId}/toggle/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/json',
    }
  })
  .then(res => {
    if (res.status === 403 || res.status === 302) {
      showToast('Please login to save items');
      return null;
    }
    return res.json();
  })
  .then(data => {
    if (!data) return;
    if (data.wishlisted) {
      btn.textContent = '❤️';
      btn.classList.add('active');
      if (btn.id === 'detail-wish-btn') btn.textContent = '❤️ Saved';
      showToast('Saved to wishlist ❤️');
    } else {
      btn.textContent = '🤍';
      btn.classList.remove('active');
      if (btn.id === 'detail-wish-btn') btn.textContent = '🤍 Add to Wishlist';
      showToast('Removed from wishlist');
    }
  })
  .catch(() => showToast('Error updating wishlist'));
}


/* ──────── CSRF Token Helper ──────── */
function getCsrfToken() {
  // Try from form hidden input first
  const input = document.querySelector('[name=csrfmiddlewaretoken]');
  if (input) return input.value;
  // Fallback to cookie
  const cookies = document.cookie.split('; ');
  for (const c of cookies) {
    if (c.startsWith('csrftoken=')) return c.split('=')[1];
  }
  return '';
}


/* ──────── Profile Tabs ──────── */
function switchTab(tab, el) {
  document.querySelectorAll('.ptab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.ptab-content').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  const content = document.getElementById('ptab-' + tab);
  if (content) content.classList.add('active');
}


/* ──────── Image Preview for Sell Form ──────── */
function previewImage(input) {
  const preview = document.getElementById('img-preview');
  if (!preview) return;
  preview.innerHTML = '';
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      preview.innerHTML = `
        <div class="preview-item">
          <img src="${e.target.result}" alt="Preview" />
          <button type="button" class="preview-remove" onclick="removeImage()">✕</button>
        </div>`;
    };
    reader.readAsDataURL(input.files[0]);
  }
}

function removeImage() {
  const input = document.getElementById('file-input');
  if (input) input.value = '';
  const preview = document.getElementById('img-preview');
  if (preview) preview.innerHTML = '';
}


/* ──────── Character Count ──────── */
function updateCharCount(el, countId, max) {
  const count = document.getElementById(countId);
  if (count) count.textContent = el.value.length;
}


/* ──────── Smooth Scroll Reveal ──────── */
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1 });

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.product-card, .college-card, .cat-card, .form-card').forEach(el => {
    el.classList.add('reveal');
    observer.observe(el);
  });
});


/* ──────── Navbar Scroll Effect ──────── */
let lastScroll = 0;
window.addEventListener('scroll', () => {
  const nav = document.querySelector('nav');
  if (!nav) return;
  const currentScroll = window.pageYOffset;
  if (currentScroll > 60) {
    nav.classList.add('scrolled');
  } else {
    nav.classList.remove('scrolled');
  }
  lastScroll = currentScroll;
});


/* ──────── Upload Zone Drag & Drop ──────── */
document.addEventListener('DOMContentLoaded', () => {
  const zone = document.querySelector('.upload-zone');
  if (!zone) return;

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => {
    zone.classList.remove('dragover');
  });
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const input = document.getElementById('file-input');
    if (input && e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      previewImage(input);
    }
  });
});
