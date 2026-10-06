document.addEventListener("DOMContentLoaded", () => {
  // Los catálogos comparten la misma hoja móvil que Caja: una franja superior
  // para arrastrar y un alto que nace del contenido del formulario.
  document.querySelectorAll(".catalog-mobile-modal").forEach((modal) => {
    modal.classList.add("modal-sheet-mobile", "modal-sheet-mobile--auto");
    const header = modal.querySelector(".modal-header");
    if (header && !header.querySelector(".modal-sheet-handle")) {
      const handle = document.createElement("span");
      handle.className = "modal-sheet-handle";
      handle.setAttribute("aria-hidden", "true");
      header.prepend(handle);
    }
  });

  const tables = document.querySelectorAll(".catalog-mobile-table");

  document.querySelectorAll(".catalog-mobile-search").forEach((search) => {
    const input = search.querySelector("input");
    if (!input || search.querySelector(".catalog-mobile-search__intro")) return;
    const intro = document.createElement("div");
    intro.className = "catalog-mobile-search__intro";
    intro.innerHTML = `<span><i class="bx bx-package" aria-hidden="true"></i></span><div><strong>Buscar registros</strong><small>Consulta por nombre o código.</small></div>`;
    search.prepend(intro);
  });

  tables.forEach((table) => {
    const headers = [...table.querySelectorAll("thead th")].map((header) => header.textContent.trim());
    const headerKeys = headers.map((header) => header.toLocaleLowerCase());
    const list = document.createElement("section");
    list.className = "catalog-mobile-list";
    list.setAttribute("aria-label", "Registros");

    const rows = [...table.querySelectorAll("tbody tr")];
    rows.forEach((row) => {
      const cells = [...row.children];
      if (!cells.length) return;
      if (cells.length === 1 && cells[0].hasAttribute("colspan")) {
        const empty = document.createElement("div");
        empty.className = "catalog-mobile-empty";
        empty.innerHTML = `<i class="bx bx-package" aria-hidden="true"></i><strong>${cells[0].textContent.trim()}</strong>`;
        list.appendChild(empty);
        return;
      }

      const titleCell = cells[1] || cells[0];
      const statusIndex = headerKeys.findIndex((header) => header.includes("estado"));
      const actionsIndex = headerKeys.findIndex((header) => header.includes("acciones"));
      const statusCell = statusIndex >= 0 ? cells[statusIndex] : null;
      const actionsCell = actionsIndex >= 0 ? cells[actionsIndex] : null;
      const card = document.createElement("article");
      card.className = "catalog-mobile-card";
      if (row.dataset.detailUrl) {
        card.dataset.detailUrl = row.dataset.detailUrl;
        card.tabIndex = 0;
        card.setAttribute("role", "link");
      }
      card.innerHTML = `<header class="catalog-mobile-card__header"><span class="catalog-mobile-card__icon"><i class="bx bx-package" aria-hidden="true"></i></span><span class="catalog-mobile-card__title"><small>${headers[0] || "Registro"} ${cells[0].textContent.trim()}</small><strong>${titleCell.textContent.trim()}</strong></span>${statusCell ? `<span class="catalog-mobile-card__status">${statusCell.innerHTML}</span>` : ""}</header>`;

      const fields = document.createElement("div");
      fields.className = "catalog-mobile-card__fields";
      cells.forEach((cell, index) => {
        if (index < 2 || index === statusIndex || index === actionsIndex) return;
        const field = document.createElement("div");
        field.className = "catalog-mobile-card__field";
        field.innerHTML = `<small>${headers[index] || "Detalle"}</small><strong>${cell.innerHTML}</strong>`;
        fields.appendChild(field);
      });
      if (fields.children.length) card.appendChild(fields);

      if (actionsCell?.querySelector("button, a")) {
        const footer = document.createElement("footer");
        footer.className = "catalog-mobile-card__footer";
        [...actionsCell.querySelectorAll("button, a")].forEach((action, index) => {
          const clone = action.cloneNode(true);
          clone.dataset.catalogSourceAction = `${row.rowIndex}-${index}`;
          action.dataset.catalogSourceAction = clone.dataset.catalogSourceAction;
          const icon = clone.querySelector("i")?.outerHTML || "";
          let label = clone.title || "Acción";
          if (clone.classList.contains("btn-edit")) label = "Editar";
          if (clone.classList.contains("btn-delete") || clone.classList.contains("btn-danger")) label = "Eliminar";
          if (clone.classList.contains("btn-pdf")) label = "PDF";
          if (clone.classList.contains("btn-abono-pagar") || clone.classList.contains("btn-abono-cobrar")) label = "Abonar";
          clone.innerHTML = `${icon}<span>${label}</span>`;
          footer.appendChild(clone);
        });
        card.appendChild(footer);
      }
      if (card.dataset.detailUrl) {
        const abrirDetalle = (event) => {
          if (event.target.closest("button, a, input, select, textarea")) return;
          window.location.assign(card.dataset.detailUrl);
        };
        card.addEventListener("click", abrirDetalle);
        card.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            window.location.assign(card.dataset.detailUrl);
          }
        });
      }
      list.appendChild(card);
    });

    table.closest(".tabla-container")?.insertAdjacentElement("afterend", list);
  });

  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-catalog-source-action]");
    if (!action || action.closest(".tabla-container")) return;
    const source = document.querySelector(`.tabla-container [data-catalog-source-action="${action.dataset.catalogSourceAction}"]`);
    if (!source) return;
    event.preventDefault();
    source.click();
  });
});
