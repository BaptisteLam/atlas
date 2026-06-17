/* =============================================================
   ATLAS — interactions partagées (Aurora)
   ============================================================= */
(function () {
  'use strict';
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Constellation canvas ─────────────────────────────── */
  function initCanvas(canvas) {
    var ctx = canvas.getContext('2d');
    if (!ctx) return;
    var w = 0, h = 0, raf = null;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    var pts = [];

    function resize() {
      var r = canvas.getBoundingClientRect();
      w = r.width; h = r.height;
      if (!w || !h) return;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    var N = Math.max(30, Math.min(72, Math.floor(w / 22)));
    for (var i = 0; i < N; i++) {
      pts.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - .5) * .22, vy: (Math.random() - .5) * .22 });
    }
    if ('ResizeObserver' in window) new ResizeObserver(resize).observe(canvas);

    function draw() {
      ctx.clearRect(0, 0, w, h);
      for (var k = 0; k < pts.length; k++) {
        var p = pts[k];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
      }
      for (var a = 0; a < pts.length; a++) {
        for (var b = a + 1; b < pts.length; b++) {
          var pa = pts[a], pb = pts[b];
          var dist = Math.hypot(pa.x - pb.x, pa.y - pb.y);
          if (dist < 124) {
            ctx.strokeStyle = 'rgba(59,130,246,' + (0.18 * (1 - dist / 124)) + ')';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
          }
        }
      }
      for (var c = 0; c < pts.length; c++) {
        ctx.fillStyle = 'rgba(147,197,253,.7)';
        ctx.beginPath(); ctx.arc(pts[c].x, pts[c].y, 1.4, 0, Math.PI * 2); ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    }
    if (reduced) { draw(); cancelAnimationFrame(raf); } else { draw(); }
  }
  document.querySelectorAll('[data-constellation]').forEach(initCanvas);

  /* ── Cursor glow ──────────────────────────────────────── */
  document.querySelectorAll('[data-glowzone]').forEach(function (zone) {
    var glow = zone.querySelector('[data-glow]');
    if (!glow) return;
    zone.addEventListener('mousemove', function (e) {
      var r = zone.getBoundingClientRect();
      glow.style.left = (e.clientX - r.left) + 'px';
      glow.style.top = (e.clientY - r.top) + 'px';
      glow.style.opacity = '1';
    });
    zone.addEventListener('mouseleave', function () { glow.style.opacity = '0'; });
  });

  /* ── Scroll reveals ───────────────────────────────────── */
  var revealItems = [].slice.call(document.querySelectorAll('[data-reveal]'));
  revealItems.forEach(function (el) { el.classList.add('r-hidden'); });

  function show(el) {
    var delay = parseFloat(el.getAttribute('data-delay') || '0');
    setTimeout(function () { el.classList.remove('r-hidden'); el.classList.add('r-visible'); }, delay);
  }

  if ('IntersectionObserver' in window) {
    var revealIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        show(e.target);
        revealIO.unobserve(e.target);
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -5% 0px' });

    requestAnimationFrame(function () {
      var vh = window.innerHeight;
      revealItems.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < vh * 0.98 && r.bottom > 0) { el.classList.remove('r-hidden'); el.classList.add('r-visible'); }
        else { revealIO.observe(el); }
      });
    });
  } else {
    revealItems.forEach(function (el) { el.classList.remove('r-hidden'); el.classList.add('r-visible'); });
  }

  /* ── Animated counters ────────────────────────────────── */
  function animateCount(el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var dur = 1500, start = performance.now();
    function step(now) {
      var t = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      var val = target * eased;
      el.textContent = (target % 1 !== 0) ? val.toFixed(1) : Math.round(val).toString();
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  if ('IntersectionObserver' in window) {
    var counterIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        animateCount(e.target);
        counterIO.unobserve(e.target);
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('[data-count]').forEach(function (el) { counterIO.observe(el); });
  }

  /* ── Parallax + solar spin (scroll) ───────────────────── */
  var scope = document.getElementById('atlas-root') || document.body;
  var parallaxEls = [].slice.call(document.querySelectorAll('[data-parallax]')).map(function (el) { return { el: el, s: parseFloat(el.getAttribute('data-parallax')) }; });
  var spinEls = [].slice.call(document.querySelectorAll('[data-scrollspin]')).map(function (el) { return { el: el, s: parseFloat(el.getAttribute('data-scrollspin')) }; });
  var ticking = false;
  function scrolled() { var r = scope.getBoundingClientRect(); return Math.max(0, -r.top); }
  function updateParallax() {
    var y = scrolled();
    parallaxEls.forEach(function (o) { o.el.style.transform = 'translate3d(0,' + (y * o.s).toFixed(1) + 'px,0)'; });
    spinEls.forEach(function (o) {
      var sc = (1 + Math.min(y, 1400) * 0.00018).toFixed(4);
      o.el.style.transform = 'rotate(' + (y * o.s).toFixed(2) + 'deg) scale(' + sc + ')';
    });
    ticking = false;
  }
  if (!reduced && (parallaxEls.length || spinEls.length)) {
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(updateParallax); } }, { passive: true, capture: true });
    updateParallax();
  }

  /* ── Sticky nav shade ─────────────────────────────────── */
  var nav = document.querySelector('.nav');
  if (nav) {
    var onScroll = function () { nav.classList.toggle('scrolled', window.scrollY > 12); };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Dropdown (desktop) ───────────────────────────────── */
  document.querySelectorAll('.has-drop').forEach(function (dd) {
    var toggle = dd.querySelector('.drop-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var wasOpen = dd.classList.contains('open');
      document.querySelectorAll('.has-drop.open').forEach(function (o) { o.classList.remove('open'); });
      if (!wasOpen) dd.classList.add('open');
    });
  });
  document.addEventListener('click', function () {
    document.querySelectorAll('.has-drop.open').forEach(function (o) { o.classList.remove('open'); });
  });

  /* ── Mobile menu ──────────────────────────────────────── */
  var burger = document.querySelector('.nav-burger');
  var mobile = document.querySelector('.mobile-menu');
  if (burger && mobile) {
    var closeBtn = mobile.querySelector('.mm-close');
    function openM() { mobile.classList.add('open'); document.body.style.overflow = 'hidden'; }
    function closeM() { mobile.classList.remove('open'); document.body.style.overflow = ''; }
    burger.addEventListener('click', openM);
    if (closeBtn) closeBtn.addEventListener('click', closeM);
    mobile.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', closeM); });
    window.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeM(); });
  }

  /* ── FAQ accordion ────────────────────────────────────── */
  var faqItems = [].slice.call(document.querySelectorAll('[data-faq]'));
  faqItems.forEach(function (item) {
    var q = item.querySelector('[data-faq-q]');
    var a = item.querySelector('[data-faq-a]');
    var icon = item.querySelector('[data-faq-icon]');
    if (!q || !a) return;
    q.addEventListener('click', function () {
      var open = item._open === true;
      faqItems.forEach(function (o) {
        if (o._open) {
          o.querySelector('[data-faq-a]').style.maxHeight = '0px';
          var i = o.querySelector('[data-faq-icon]'); if (i) i.style.transform = 'rotate(0deg)';
          o.style.borderColor = 'rgba(255,255,255,.1)';
          o.style.background = 'rgba(255,255,255,.035)';
          o._open = false;
        }
      });
      if (!open) {
        a.style.maxHeight = a.scrollHeight + 'px';
        if (icon) icon.style.transform = 'rotate(45deg)';
        item.style.borderColor = 'rgba(59,130,246,.5)';
        item.style.background = 'rgba(59,130,246,.06)';
        item._open = true;
      }
    });
  });
})();
