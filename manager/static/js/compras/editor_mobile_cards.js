(() => {
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);

  const isMobile = () => window.matchMedia("(max-width: 1032px)").matches;

  const render = () => {
    const table = document.getElementById("tablacont");
    const body = table?.querySelector("tbody");
    const host = table?.closest(".tablaencompras");
    if (!table || !body || !host) return;

    let list = host.querySelector(".compras-editor-mobile-list");
    if (!list) {
      list = document.createElement("section");
      list.className = "compras-editor-mobile-list";
      list.setAttribute("aria-label", "Productos agregados");
      host.insertBefore(list, host.querySelector("#paginadorProv") || null);
    }
    list.replaceChildren();
    if (!isMobile) return;

    [...body.querySelectorAll("tr")].filter((row) => !row.hidden).forEach((row, index) => {
      const cells = row.children;
      const name = cells[1]?.textContent.trim() || "Producto";
      const presentation = cells[2]?.textContent.trim() || "Sin presentación";
      const sku = cells[3]?.textContent.trim() || "Sin SKU";
      const brand = row.dataset.marca || "Sin marca";
      const price = row.querySelector(".precio-input");
      const tax = row.querySelector(".impuesto-input");
      const quantity = row.querySelector(".cantidad-input");
      const remove = row.querySelector(".eliminar-fila");
      const card = document.createElement("article");
      card.className = "compras-editor-mobile-card";
      card.innerHTML = `<header><span class="compras-editor-mobile-card__icon"><i class="bx bx-package"></i></span><div><small>Producto ${index + 1}</small><strong>${escapeHtml(name)}</strong></div></header><div class="compras-editor-mobile-card__meta"><div><i class="bx bx-purchase-tag"></i><span><small>Presentación</small><strong>${escapeHtml(presentation)}</strong></span></div><div><i class="bx bx-purchase-tag-alt"></i><span><small>Marca</small><strong>${escapeHtml(brand)}</strong></span></div><div class="compras-editor-mobile-card__sku"><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escapeHtml(sku)}</strong></span></div></div><div class="compras-editor-mobile-card__controls"></div><footer></footer>`;
      const controls = card.querySelector(".compras-editor-mobile-card__controls");
      [[price, "Precio"], [tax, "Impuesto %"], [quantity, "Cantidad"]].forEach(([source, label]) => {
        if (!source) return;
        const field = document.createElement("label");
        field.innerHTML = `<small>${label}</small>`;
        const mirror = source.cloneNode(true);
        mirror.removeAttribute("id");
        mirror.type = "number";
        mirror.step = label === "Cantidad" ? "1" : "any";
        mirror.min = "0";
        mirror.inputMode = label === "Cantidad" ? "numeric" : "decimal";
        mirror.style.pointerEvents = "auto";
        mirror.addEventListener("input", () => {
          source.value = mirror.value;
          source.dispatchEvent(new Event("input", { bubbles: true }));
        });
        field.appendChild(mirror);
        controls.appendChild(field);
      });
      if (remove) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-danger";
        button.innerHTML = '<i class="bx bx-trash"></i><span>Eliminar</span>';
        button.addEventListener("click", () => remove.click());
        card.querySelector("footer").appendChild(button);
      }
      list.appendChild(card);
    });
  };

  const renderTransfer = () => {
    const body = document.getElementById("tablaTraslados");
    const host = body?.closest(".traslado-editor-mobile");
    if (!body || !host) return;
    let list = host.querySelector(".traslados-editor-mobile-list");
    if (!list) {
      list = document.createElement("section");
      list.className = "traslados-editor-mobile-list";
      list.setAttribute("aria-label", "Productos a trasladar");
      host.appendChild(list);
    }
    list.replaceChildren();
    if (!isMobile()) return;
    [...body.querySelectorAll("tr")].forEach((row, index) => {
      const cells = row.children;
      const name = cells[1]?.textContent.trim() || "Producto";
      const sku = cells[2]?.textContent.trim() || "Sin SKU";
      const stock = cells[3]?.textContent.trim() || "0";
      const quantity = row.querySelector(".cantidad-final");
      const remove = row.querySelector(".eliminar-traslado");
      const card = document.createElement("article");
      card.className = "traslados-editor-mobile-card";
      card.innerHTML = `<header><span class="traslados-editor-mobile-card__icon"><i class="bx bx-transfer-alt"></i></span><div><small>Producto ${index + 1}</small><strong>${escapeHtml(name)}</strong></div></header><div class="traslados-editor-mobile-card__meta"><div><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escapeHtml(sku)}</strong></span></div><div><i class="bx bx-box"></i><span><small>Stock disponible</small><strong>${escapeHtml(stock)}</strong></span></div></div><div class="traslados-editor-mobile-card__controls"></div><footer></footer>`;
      if (quantity) {
        const field = document.createElement("label");
        field.innerHTML = "<small>Cantidad a mover</small>";
        const mirror = quantity.cloneNode(true);
        mirror.removeAttribute("id");
        mirror.type = "number";
        mirror.inputMode = "numeric";
        mirror.style.pointerEvents = "auto";
        mirror.addEventListener("input", () => {
          quantity.value = mirror.value;
          quantity.dispatchEvent(new Event("input", { bubbles: true }));
          mirror.value = quantity.value;
        });
        field.appendChild(mirror);
        card.querySelector(".traslados-editor-mobile-card__controls").appendChild(field);
      }
      if (remove) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-danger";
        button.innerHTML = '<i class="bx bx-trash"></i><span>Eliminar</span>';
        button.addEventListener("click", () => remove.click());
        card.querySelector("footer").appendChild(button);
      }
      list.appendChild(card);
    });
  };

  const renderConfirmation = () => {
    const body = document.getElementById("tablaDetallesModal");
    const modal = body?.closest(".compras-mobile-modal");
    const list = modal?.querySelector(".compras-confirmar-mobile-list");
    if (!body || !list) return;
    list.replaceChildren();
    if (!isMobile()) return;

    [...body.querySelectorAll("tr")].forEach((row, index) => {
      const cells = row.children;
      const name = cells[1]?.textContent.trim() || "Producto";
      const presentation = cells[2]?.textContent.trim() || "Sin presentación";
      const sku = cells[3]?.textContent.trim() || "Sin SKU";
      const quantity = cells[4]?.textContent.trim() || "0";
      const price = cells[5]?.textContent.trim() || "L. 0.00";
      const total = cells[cells.length - 1]?.textContent.trim() || "L. 0.00";
      const tax = cells[6]?.textContent.trim() || "0%";
      const card = document.createElement("article");
      card.className = "compras-confirmar-mobile-card";
      card.innerHTML = `<header><span class="compras-confirmar-mobile-card__icon"><i class="bx bx-package"></i></span><div><small>Producto ${index + 1}</small><strong>${escapeHtml(name)}</strong></div><span class="compras-confirmar-mobile-card__total">${escapeHtml(total)}</span></header><div class="compras-confirmar-mobile-card__meta"><div><i class="bx bx-purchase-tag"></i><span><small>Presentación</small><strong>${escapeHtml(presentation)}</strong></span></div><div><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escapeHtml(sku)}</strong></span></div></div><div class="compras-confirmar-mobile-card__figures"><div><small>Cantidad</small><strong>${escapeHtml(quantity)}</strong></div><div><small>Precio</small><strong>${escapeHtml(price)}</strong></div><div><small>Impuesto</small><strong>${escapeHtml(tax)}</strong></div></div>`;
      list.appendChild(card);
    });
  };

  const renderTransferConfirmation = () => {
    const body = document.getElementById("tablaPreviewTraslado");
    const modal = body?.closest(".traslado-mobile-modal");
    const list = modal?.querySelector(".traslados-confirmar-mobile-list");
    if (!body || !list) return;
    list.replaceChildren();
    if (!isMobile()) return;
    [...body.querySelectorAll("tr")].forEach((row, index) => {
      const cells = row.children;
      const name = cells[1]?.textContent.trim() || "Producto";
      const sku = cells[2]?.textContent.trim() || "Sin SKU";
      const stock = cells[3]?.textContent.trim() || "0";
      const quantity = cells[4]?.textContent.trim() || "0";
      const card = document.createElement("article");
      card.className = "traslados-confirmar-mobile-card";
      card.innerHTML = `<header><span class="traslados-confirmar-mobile-card__icon"><i class="bx bx-transfer-alt"></i></span><div><small>Producto ${index + 1}</small><strong>${escapeHtml(name)}</strong></div><span class="traslados-confirmar-mobile-card__quantity">${escapeHtml(quantity)}</span></header><div class="traslados-confirmar-mobile-card__meta"><div><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escapeHtml(sku)}</strong></span></div><div><i class="bx bx-box"></i><span><small>Stock disponible</small><strong>${escapeHtml(stock)}</strong></span></div></div><div class="traslados-confirmar-mobile-card__amount"><small>Cantidad a mover</small><strong>${escapeHtml(quantity)}</strong></div>`;
      list.appendChild(card);
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.querySelector("#tablacont tbody");
    if (body) new MutationObserver(render).observe(body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["hidden"],
    });
    const transferBody = document.getElementById("tablaTraslados");
    if (transferBody) new MutationObserver(renderTransfer).observe(transferBody, { childList: true, subtree: true });
    const confirmationBody = document.getElementById("tablaDetallesModal");
    if (confirmationBody) new MutationObserver(renderConfirmation).observe(confirmationBody, { childList: true, subtree: true });
    const transferConfirmationBody = document.getElementById("tablaPreviewTraslado");
    if (transferConfirmationBody) new MutationObserver(renderTransferConfirmation).observe(transferConfirmationBody, { childList: true, subtree: true });
    const breakpoint = window.matchMedia("(max-width: 1032px)");
    breakpoint.addEventListener?.("change", () => {
      render();
      renderTransfer();
      renderConfirmation();
      renderTransferConfirmation();
    });
    render();
    renderTransfer();
    renderConfirmation();
    renderTransferConfirmation();
  });
})();
