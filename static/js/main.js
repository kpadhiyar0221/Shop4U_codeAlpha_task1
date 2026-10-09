// Shop4U - small helpers (no libraries needed)
document.addEventListener("DOMContentLoaded", function () {
  // Mobile menu toggle
  var toggle = document.querySelector(".nav-toggle");
  var menu = document.getElementById("nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Dismiss messages (and auto-hide after 6 seconds)
  document.querySelectorAll(".message").forEach(function (box) {
    var close = box.querySelector(".message-close");
    if (close) close.addEventListener("click", function () { box.remove(); });
    setTimeout(function () { if (box.parentNode) box.remove(); }, 6000);
  });

  // Quantity +/- buttons (product page); never exceeds stock
  document.querySelectorAll(".qty").forEach(function (wrap) {
    var input = wrap.querySelector("input");
    var max = parseInt(wrap.dataset.max, 10) || 1;
    wrap.querySelectorAll(".qty-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var v = (parseInt(input.value, 10) || 1) + parseInt(btn.dataset.step, 10);
        input.value = Math.min(Math.max(v, 1), max);
      });
    });
    input.addEventListener("change", function () {
      var v = parseInt(input.value, 10) || 1;
      input.value = Math.min(Math.max(v, 1), max);
    });
  });

  // Disable the submit button after click (checkout/contact) to avoid double orders
  document.querySelectorAll("form[data-disable-on-submit]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var btn = form.querySelector("button[type=submit]");
      if (!btn || btn.disabled) return;
      var text = btn.dataset.loadingText || "Please wait...";
      setTimeout(function () { btn.disabled = true; btn.textContent = text; }, 0);
    });
  });

  // Re-enable buttons if the user comes back with the Back button
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) window.location.reload();
  });
});
