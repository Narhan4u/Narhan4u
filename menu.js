/* =========================================================
   SAMFIK FOODS MENU
   Edit dishes, options and prices here.
   - price: number in pounds (e.g. 9.5) or null to hide it
   - option "price": extra cost for that choice (optional)
   - group "required": true -> customer must choose
   - group "max": 1 -> choose one (round buttons), otherwise tick boxes
   - img: file in /images (a coloured block shows until it exists)
   ========================================================= */
var PROTEINS = {
  name: "Choose your protein", required: true, max: 1,
  options: [
    { name: "Peppered Chicken" },
    { name: "Peppered Turkey" },
    { name: "Jerk Chicken" },
    { name: "Grilled Chicken" },
    { name: "Chicken Suya" },
    { name: "Lamb Suya" }
  ]
};
var SPICE = {
  name: "How hot?", required: true, max: 1,
  options: [{ name: "Mild" }, { name: "Medium" }, { name: "Naija hot 🌶🌶🌶" }]
};
var COLESLAW = { name: "Free coleslaw", required: false, options: [{ name: "Free coleslaw" }] };
var EXTRAS = { name: "Add a little extra", required: false, options: [{ name: "Meat Pie", price: 1.99 }, { name: "Puff Puff (3)", price: 1.50 }] };

var MENU = [
  {
    id: "rice", name: "Rice Plates",
    desc: "Choose your rice, pick your meat. Mix and match it your way.",
    items: [
      { name: "Jollof Rice", price: 9.00, img: "jollof.jpg", g: ["#e2531b", "#7a1d06"], tag: "Bestseller",
        desc: "Smoky party jollof with your choice of protein. Free coleslaw on request.",
        groups: [PROTEINS, COLESLAW, SPICE, EXTRAS] },
      { name: "Rice & Beans", price: 9.00, img: "rice-and-beans.jpg", g: ["#9a4b1c", "#3b1a08"],
        desc: "Rice & beans served with our house sauce and your choice of protein. Free coleslaw on request.",
        groups: [PROTEINS, COLESLAW, SPICE, EXTRAS] }
    ]
  },
  {
    id: "grill", name: "Suya & Grill",
    desc: "Flame-grilled and rubbed in yaji, our peanut-chilli suya spice.",
    items: [
      { name: "Chicken Suya", price: 6.99, img: "chicken-suya.jpg", g: ["#b5461a", "#3b1407"], tag: "Street classic",
        desc: "Tender chicken skewers rubbed in yaji, then flame-grilled.", groups: [SPICE] },
      { name: "Lamb Suya", price: 7.99, img: "lamb-suya.jpg", g: ["#8f2d12", "#2a0d05"], tag: "Must try",
        desc: "Thin-sliced lamb, deeply spiced and charred at the edges, with onions.", groups: [SPICE] }
    ]
  },
  {
    id: "pepper", name: "Peppered Meats",
    desc: "Fried until golden, then tossed in a fiery scotch-bonnet pepper sauce.",
    items: [
      { name: "Peppered Chicken", price: 6.99, img: "peppered-chicken.jpg", g: ["#c7321d", "#4a0e07"],
        desc: "Golden chicken tossed in our pepper sauce.", groups: [SPICE] },
      { name: "Peppered Turkey", price: 8.99, img: "peppered-turkey.jpg", g: ["#a8281a", "#3d0b05"],
        desc: "Juicy turkey tossed in our pepper sauce.", groups: [SPICE] }
    ]
  },
  {
    id: "snacks", name: "Snacks & Sides",
    desc: "Perfect on the go, or on the side.",
    items: [
      { name: "Loaded Fries", price: 5.99, img: "loaded-fries.jpg", g: ["#e0a01e", "#7a3d06"], tag: "Naija twist",
        desc: "Crispy fries piled high with suya meat, peppers and sauce.", groups: [SPICE] },
      { name: "Meat Pie", price: 1.99, img: "meat-pie.jpg", g: ["#d8a65a", "#6b3d12"],
        desc: "Buttery, flaky pastry packed with seasoned minced meat, potato and carrot.", groups: [] }
    ]
  },
  {
    id: "sweet", name: "Sweet Treats",
    desc: "Save room for these.",
    items: [
      { name: "Puff Puff", price: 1.50, img: "puff-puff.jpg", g: ["#f0b448", "#8a4a10"], tag: "Sweet treat",
        desc: "3 soft, pillowy, lightly sweet dough balls fried golden.", groups: [] }
    ]
  }
];

/* ================= Ordering logic ================= */
(function () {
  var PHONE = "447404531445";
  var catsEl = document.getElementById("menuCats");
  var listEl = document.getElementById("menuList");
  if (!catsEl || !listEl) return;

  function money(n) { return "£" + n.toFixed(2); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function imgStyle(it) { return "--img:url('images/" + it.img + "');--g1:" + it.g[0] + ";--g2:" + it.g[1]; }

  // Render categories + items
  catsEl.innerHTML = MENU.map(function (c, i) {
    return '<a href="#cat-' + c.id + '" class="' + (i === 0 ? "is-active" : "") + '" data-cat="' + c.id + '">' + esc(c.name) + "</a>";
  }).join("");
  listEl.innerHTML = MENU.map(function (c, ci) {
    return '<section class="omenu__cat" id="cat-' + c.id + '" data-cat="' + c.id + '">' +
      '<div class="omenu__catHead"><h3>' + esc(c.name) + "</h3><p>" + esc(c.desc) + "</p></div>" +
      '<div class="omenu__items">' + c.items.map(function (it, ii) {
        return '<button type="button" class="oitem" data-c="' + ci + '" data-i="' + ii + '">' +
          '<span class="oitem__text"><b>' + esc(it.name) + "</b><small>" + esc(it.desc) + "</small>" +
          '<span class="oitem__price">' + (it.price != null ? money(it.price) : "Choose options") + "</span></span>" +
          '<span class="oitem__img" style="' + imgStyle(it) + '">' + (it.tag ? '<i>' + esc(it.tag) + "</i>" : "") + '<em>+</em></span>' +
          "</button>";
      }).join("") + "</div></section>";
  }).join("");

  // Highlight active category while scrolling
  var catLinks = catsEl.querySelectorAll("a");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          catLinks.forEach(function (a) {
            var on = a.dataset.cat === en.target.dataset.cat;
            a.classList.toggle("is-active", on);
            if (on && window.innerWidth <= 900) catsEl.scrollTo({ left: a.offsetLeft - 16, behavior: "smooth" });
          });
        }
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    listEl.querySelectorAll(".omenu__cat").forEach(function (s) { io.observe(s); });
  }

  // ----- Item modal -----
  var modal = document.getElementById("itemModal");
  var optForm = document.getElementById("modalOptions");
  var qtyOut = document.getElementById("mQty");
  var addPrice = document.getElementById("modalAddPrice");
  var errEl = document.getElementById("modalError");
  var current = null, qty = 1, lastFocus = null;

  function unitPrice() {
    if (!current || current.price == null) return null;
    var extra = 0;
    optForm.querySelectorAll("input:checked").forEach(function (inp) { extra += parseFloat(inp.dataset.price || 0); });
    return current.price + extra;
  }
  function updatePrice() {
    var u = unitPrice();
    addPrice.textContent = u != null ? money(u * qty) : "";
    qtyOut.textContent = qty;
  }

  function openItem(it) {
    current = it; qty = 1; errEl.textContent = "";
    document.getElementById("modalTitle").textContent = it.name;
    document.getElementById("modalPrice").textContent = it.price != null ? money(it.price) : "";
    document.getElementById("modalDesc").textContent = it.desc;
    document.getElementById("modalImg").setAttribute("style", imgStyle(it));
    optForm.innerHTML = it.groups.map(function (g, gi) {
      var single = g.max === 1;
      return '<fieldset class="ogroup" data-g="' + gi + '"><legend><span>' + esc(g.name) + "</span>" +
        '<em class="' + (g.required ? "req" : "") + '">' + (g.required ? "Required" : "Optional") + "</em></legend>" +
        (single ? '<p class="ogroup__hint">Choose 1</p>' : "") +
        g.options.map(function (o) {
          return '<label class="opt"><input type="' + (single ? "radio" : "checkbox") + '" name="g' + gi + '" value="' + esc(o.name) + '" data-price="' + (o.price || 0) + '">' +
            '<span class="opt__box"></span><span class="opt__name">' + esc(o.name) + "</span>" +
            (o.price ? '<span class="opt__price">+' + money(o.price) + "</span>" : "") + "</label>";
        }).join("") + "</fieldset>";
    }).join("");
    updatePrice();
    lastFocus = document.activeElement;
    modal.hidden = false;
    document.body.classList.add("no-scroll");
    modal.querySelector(".modal__close").focus();
  }
  function closeItem() {
    modal.hidden = true;
    document.body.classList.remove("no-scroll");
    if (lastFocus) lastFocus.focus();
  }

  listEl.addEventListener("click", function (e) {
    var btn = e.target.closest(".oitem");
    if (btn) openItem(MENU[btn.dataset.c].items[btn.dataset.i]);
  });
  modal.addEventListener("click", function (e) { if (e.target.hasAttribute("data-close")) closeItem(); });
  optForm.addEventListener("change", function () { errEl.textContent = ""; updatePrice(); });
  document.getElementById("mQtyMinus").addEventListener("click", function () { if (qty > 1) { qty--; updatePrice(); } });
  document.getElementById("mQtyPlus").addEventListener("click", function () { if (qty < 50) { qty++; updatePrice(); } });

  document.getElementById("modalAdd").addEventListener("click", function () {
    var chosen = [], missing = null;
    current.groups.forEach(function (g, gi) {
      var picked = Array.prototype.map.call(optForm.querySelectorAll('input[name="g' + gi + '"]:checked'), function (i) { return i.value; });
      if (g.required && !picked.length && !missing) missing = g.name;
      chosen = chosen.concat(picked);
    });
    if (missing) {
      errEl.textContent = "Please choose: " + missing;
      optForm.querySelectorAll(".ogroup").forEach(function (f) {
        if (f.querySelector("legend span").textContent === missing) f.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      return;
    }
    basket.push({ name: current.name, options: chosen, qty: qty, unit: unitPrice() });
    closeItem();
    renderBasket();
    basketBtn.classList.remove("bump"); void basketBtn.offsetWidth; basketBtn.classList.add("bump");
  });

  // "Order" links on the favourites grid open that dish's options
  document.querySelectorAll("[data-open]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      e.preventDefault();
      MENU.some(function (c) {
        return c.items.some(function (it) { if (it.name === a.dataset.open) { openItem(it); return true; } });
      });
    });
  });

  // ----- Basket -----
  var basket = [];
  var basketBtn = document.getElementById("basketBtn");
  var basketEl = document.getElementById("basket");
  var itemsEl = document.getElementById("basketItems");
  var totalEl = document.getElementById("basketTotal");

  function total() {
    var t = 0;
    for (var i = 0; i < basket.length; i++) { if (basket[i].unit == null) return null; t += basket[i].unit * basket[i].qty; }
    return t;
  }
  function renderBasket() {
    var count = basket.reduce(function (n, b) { return n + b.qty; }, 0);
    var t = total();
    basketBtn.hidden = count === 0;
    document.getElementById("basketCount").textContent = count;
    document.getElementById("basketTotalBtn").textContent = t != null && count ? money(t) : "";
    itemsEl.innerHTML = basket.length ? basket.map(function (b, i) {
      return '<li><div><b>' + b.qty + "× " + esc(b.name) + "</b>" + (b.options.length ? "<small>" + esc(b.options.join(", ")) + "</small>" : "") + "</div>" +
        '<div class="basket__right">' + (b.unit != null ? "<span>" + money(b.unit * b.qty) + "</span>" : "") +
        '<button type="button" data-rm="' + i + '" aria-label="Remove ' + esc(b.name) + '">Remove</button></div></li>';
    }).join("") : '<li class="basket__empty">Your order is empty.</li>';
    totalEl.innerHTML = basket.length ? (t != null ? "<span>Total</span><b>" + money(t) + "</b>" : "<span>Total</span><b>Confirmed by us</b>") : "";
    if (!count) closeBasket();
  }
  function openBasket() { basketEl.hidden = false; document.body.classList.add("no-scroll"); }
  function closeBasket() { basketEl.hidden = true; document.body.classList.remove("no-scroll"); }

  basketBtn.addEventListener("click", openBasket);
  basketEl.addEventListener("click", function (e) {
    if (e.target.hasAttribute("data-bclose")) closeBasket();
    if (e.target.dataset.rm != null) { basket.splice(+e.target.dataset.rm, 1); renderBasket(); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (!modal.hidden) closeItem(); else if (!basketEl.hidden) closeBasket();
  });

  var bForm = document.getElementById("basketForm");
  var bNote = document.getElementById("basketNote");
  bForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var ok = true;
    ["name", "phone"].forEach(function (n) {
      var f = bForm.elements[n], bad = !f.value.trim();
      f.classList.toggle("is-invalid", bad); if (bad) ok = false;
    });
    if (!ok) { bNote.textContent = "Please add your name and phone number."; bNote.classList.remove("is-success"); return; }
    var t = total();
    var lines = ["Hi Samfik Foods! 👋 New order:", ""].concat(basket.map(function (b) {
      return "• " + b.qty + "x " + b.name + (b.options.length ? " (" + b.options.join(", ") + ")" : "") + (b.unit != null ? " " + money(b.unit * b.qty) : "");
    }));
    if (t != null) lines.push("", "Total: " + money(t));
    lines.push("", "Name: " + bForm.elements.name.value.trim(), "Phone: " + bForm.elements.phone.value.trim());
    if (bForm.elements.time.value.trim()) lines.push("Collection: " + bForm.elements.time.value.trim());
    window.open("https://wa.me/" + PHONE + "?text=" + encodeURIComponent(lines.join("\n")), "_blank", "noopener");
    bNote.textContent = "WhatsApp has opened. Just hit send and we'll confirm your order.";
    bNote.classList.add("is-success");
  });
})();
