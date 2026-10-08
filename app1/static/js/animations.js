/* ==========================================================================
   TEACH2LEARN — ANIMATION SYSTEM (vanilla JS)
   Page-load fade, scroll reveals, stagger, micro-interactions.
   No color cycling. No flashing. Respects prefers-reduced-motion.
   ========================================================================== */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------------------
     1. Page-load fade-in
     ------------------------------------------------------------------- */
  function pageLoadFade() {
    document.documentElement.classList.add("t2l-ready");
    requestAnimationFrame(function () {
      document.body.classList.add("t2l-loaded");
    });
  }

  /* ---------------------------------------------------------------------
     2. Auto-tag reveal targets
     Any of these selectors get [data-reveal] automatically if the author
     didn't already add it by hand in the template.
     ------------------------------------------------------------------- */
  function autoTagReveals() {
    var selector = [
      "section .card", ".t2l-card",
      "section h1", "section h2", "section .section-title",
      "section p", "section form",
      ".profile-mini", ".testimonial-card", ".feature-card",
      ".stats-card", ".score-box", "table", ".table-responsive",
      ".neo-input", ".skill-slide", ".process-step"
    ].join(",");

    var nodes = document.querySelectorAll(selector);
    nodes.forEach(function (el) {
      if (!el.hasAttribute("data-reveal")) {
        el.setAttribute("data-reveal", "");
      }
    });
  }

  /* ---------------------------------------------------------------------
     3. Stagger delays within a shared parent (grids, lists, rows)
     ------------------------------------------------------------------- */
  function applyStagger() {
    var groups = document.querySelectorAll(
      ".row, .skills-track, .footer-links, tbody"
    );
    groups.forEach(function (group) {
      var children = group.querySelectorAll(":scope > [data-reveal], :scope > * [data-reveal]");
      var direct = Array.prototype.filter.call(
        group.children,
        function (c) { return c.hasAttribute("data-reveal") || c.querySelector("[data-reveal]"); }
      );
      direct.forEach(function (child, i) {
        var target = child.hasAttribute("data-reveal") ? child : child.querySelector("[data-reveal]");
        if (target && !target.style.getPropertyValue("--d")) {
          target.style.setProperty("--d", Math.min(i * 70, 420) + "ms");
        }
      });
    });
  }

  /* ---------------------------------------------------------------------
     4. IntersectionObserver reveal
     ------------------------------------------------------------------- */
  function initReveal() {
    var targets = document.querySelectorAll("[data-reveal]");

    if (reduceMotion || !("IntersectionObserver" in window)) {
      targets.forEach(function (el) { el.classList.add("is-visible"); });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries, obs) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    targets.forEach(function (el) { observer.observe(el); });
  }

  /* ---------------------------------------------------------------------
     5. Navbar scroll state
     ------------------------------------------------------------------- */
  function initNavbarScroll() {
    var nav = document.querySelector(".t2l-navbar");
    if (!nav) return;
    function onScroll() {
      nav.classList.toggle("is-scrolled", window.scrollY > 12);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------------------------------------------------------------------
     6. Button ripple micro-interaction (subtle, no color cycling)
     ------------------------------------------------------------------- */
  function initButtonRipple() {
    if (reduceMotion) return;
    document.querySelectorAll(".btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        var rect = btn.getBoundingClientRect();
        var ripple = document.createElement("span");
        var size = Math.max(rect.width, rect.height);
        ripple.style.position = "absolute";
        ripple.style.left = (e.clientX - rect.left - size / 2) + "px";
        ripple.style.top = (e.clientY - rect.top - size / 2) + "px";
        ripple.style.width = ripple.style.height = size + "px";
        ripple.style.borderRadius = "50%";
        ripple.style.background = "rgba(255,255,255,0.35)";
        ripple.style.transform = "scale(0)";
        ripple.style.opacity = "1";
        ripple.style.pointerEvents = "none";
        ripple.style.transition = "transform .5s ease, opacity .6s ease";
        var prevPosition = getComputedStyle(btn).position;
        if (prevPosition === "static") btn.style.position = "relative";
        btn.style.overflow = "hidden";
        btn.appendChild(ripple);
        requestAnimationFrame(function () {
          ripple.style.transform = "scale(2.2)";
          ripple.style.opacity = "0";
        });
        setTimeout(function () { ripple.remove(); }, 650);
      });
    });
  }

  /* ---------------------------------------------------------------------
     7. Active nav-link highlight based on current path
     ------------------------------------------------------------------- */
  function highlightActiveLink() {
    var path = window.location.pathname.replace(/\/$/, "");
    document.querySelectorAll(".t2l-navbar .nav-link").forEach(function (link) {
      var linkPath = (link.getAttribute("href") || "").replace(/\/$/, "");
      if (linkPath && linkPath === path) {
        link.classList.add("active");
      }
    });
  }

  /* ---------------------------------------------------------------------
     Init
     ------------------------------------------------------------------- */
  document.addEventListener("DOMContentLoaded", function () {
    pageLoadFade();
    autoTagReveals();
    applyStagger();
    initReveal();
    initNavbarScroll();
    initButtonRipple();
    highlightActiveLink();
  });
})();
