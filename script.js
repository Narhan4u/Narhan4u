(function () {
  var PHONE = "447404531445";

  // Year
  document.getElementById("year").textContent = new Date().getFullYear();

  // Sticky nav style
  var nav = document.getElementById("nav");
  function onScroll() { nav.classList.toggle("is-scrolled", window.scrollY > 30); }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Mobile menu
  var toggle = document.getElementById("navToggle");
  var links = document.getElementById("navLinks");
  toggle.addEventListener("click", function () {
    var open = links.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open);
  });
  links.addEventListener("click", function (e) {
    if (e.target.tagName === "A") { links.classList.remove("is-open"); toggle.setAttribute("aria-expanded", "false"); }
  });

  // Open / closed badge + today's hours (UK time)
  try {
    var parts = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/London", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(new Date());
    var get = function (t) { return (parts.find(function (p) { return p.type === t; }) || {}).value; };
    var dayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    var day = dayMap[get("weekday")];
    var mins = parseInt(get("hour"), 10) * 60 + parseInt(get("minute"), 10);
    var isOpen = day >= 1 && day <= 6 && mins >= 600 && mins < 990;
    var badge = document.getElementById("openBadge");
    badge.classList.add(isOpen ? "is-open" : "is-closed");
    badge.querySelector("b").textContent = isOpen ? "Open now · till 4:30pm" : "Closed · opens " + (day === 6 && mins >= 990 || day === 0 ? "Mon 10am" : (mins < 600 ? "10am today" : "10am tomorrow"));
    var row = document.querySelector('#hoursTable tr[data-day="' + day + '"]');
    if (row) row.classList.add("is-today");
  } catch (e) { /* ignore */ }

  // Menu filter tabs
  var tabs = document.querySelectorAll(".tab");
  var dishes = document.querySelectorAll(".dish");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) { t.classList.remove("is-active"); });
      tab.classList.add("is-active");
      var f = tab.dataset.filter;
      dishes.forEach(function (d) {
        d.classList.toggle("is-hidden", f !== "all" && d.dataset.cat !== f && !d.classList.contains("dish--cta"));
      });
    });
  });

  // "Order" links prefill the form
  var form = document.getElementById("leadForm");
  document.querySelectorAll("[data-dish], [data-type]").forEach(function (el) {
    el.addEventListener("click", function () {
      if (el.dataset.dish) {
        var msg = form.elements.message;
        msg.value = (msg.value ? msg.value + "\n" : "") + "1x " + el.dataset.dish;
        form.elements.type.value = "Takeaway pre-order";
      }
      if (el.dataset.type) form.elements.type.value = el.dataset.type;
      setTimeout(function () { form.elements.name.focus({ preventScroll: true }); }, 600);
    });
  });

  // Form -> WhatsApp
  var note = document.getElementById("formNote");
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var ok = true;
    ["name", "phone"].forEach(function (n) {
      var f = form.elements[n];
      var bad = !f.value.trim();
      f.classList.toggle("is-invalid", bad);
      if (bad) ok = false;
    });
    if (!ok) { note.textContent = "Please add your name and phone number."; note.classList.remove("is-success"); return; }

    var d = form.elements;
    var lines = [
      "Hi Samfik Foods! 👋",
      "Request: " + d.type.value,
      "Name: " + d.name.value.trim(),
      "Phone: " + d.phone.value.trim()
    ];
    if (d.date.value) lines.push("Date: " + d.date.value);
    if (d.people.value) lines.push("People: " + d.people.value);
    if (d.message.value.trim()) lines.push("Order / message: " + d.message.value.trim());

    window.open("https://wa.me/" + PHONE + "?text=" + encodeURIComponent(lines.join("\n")), "_blank", "noopener");
    note.textContent = "Thanks! WhatsApp has opened. Just hit send and we'll get back to you.";
    note.classList.add("is-success");
  });


  // Reveal on scroll
  var els = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("is-visible"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    els.forEach(function (el, i) { el.style.transitionDelay = (i % 4) * 70 + "ms"; io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add("is-visible"); });
  }
})();
