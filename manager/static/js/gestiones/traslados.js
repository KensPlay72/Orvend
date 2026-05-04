let inventarioSeleccionadoGlobal = {};

document.getElementById("modalregis").addEventListener("show.bs.modal", (e) => {
  const origen = document.getElementById("ubicacion_origen").value;

  if (!origen) {
    e.preventDefault();

    Swal.fire({
      title: "Ubicación requerida",
      text: "Debes seleccionar una ubicación de origen antes de continuar.",
      icon: "warning",
      confirmButtonText: "OK",
      customClass: { confirmButton: "classbotones" },
    });
  }
});

// debounce
function debounce(func, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

// dropdown ubicaciones (igual que lo tenías)
function initDropdown(hiddenInputId, remoteSearchFn = null) {
  const hiddenInput = document.getElementById(hiddenInputId);
  const container = hiddenInput.nextElementSibling;

  const selectBtn = container.querySelector("button");
  const dropdown = container.querySelector(".dropdown-menu");
  const searchInput = container.querySelector(".search-box input");
  const optionsContainer = container.querySelector(".options");

  selectBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("show");
    searchInput.focus();

    if (dropdown.classList.contains("show") && remoteSearchFn) {
      optionsContainer.innerHTML = `<div class="list-group-item">Cargando...</div>`;
      await remoteSearchFn("", optionsContainer);
    }
  });

  optionsContainer.addEventListener("click", async (e) => {
    const item = e.target.closest("button");
    if (!item) return;

    hiddenInput.value = item.dataset.value;
    selectBtn.textContent = item.dataset.label;
    dropdown.classList.remove("show");

    if (hiddenInputId === "ubicacion_origen") {
      await cargarInventarioEnModal(item.dataset.value);
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });
}

// fetch ubicaciones
async function fetchUbicaciones(term, optionsContainer) {
  const res = await fetch(
    `/manager/ubicaciones/search/?search=${encodeURIComponent(term)}`,
  );
  const data = await res.json();

  optionsContainer.innerHTML = "";

  data.forEach((u) => {
    optionsContainer.innerHTML += `
      <button type="button"
        class="list-group-item list-group-item-action"
        data-value="${u.id}"
        data-label="${u.nombre} | ${u.codigo || ""}">
        ${u.nombre} | ${u.codigo || ""}
      </button>
    `;
  });
}

initDropdown("ubicacion_origen", fetchUbicaciones);
initDropdown("ubicacion_destino", fetchUbicaciones);

// cargar inventario
async function cargarInventarioEnModal(ubicacionId) {
  const contenedor = document.getElementById("contenedorProductosAjax");
  contenedor.innerHTML = `<div class="text-center py-4">Cargando...</div>`;

  inventarioSeleccionadoGlobal = {};

  const res = await fetch(`/manager/inventario/ubicacion/${ubicacionId}/`);
  const data = await res.json();

  contenedor.innerHTML = "";

  data.forEach((prod) => {
    const div = document.createElement("div");

    div.className =
      "productosstyle producto-item d-flex align-items-center w-100";

    div.innerHTML = `
      <div class="me-3">
        <img src="${prod.imagen || "/static/img/default.png"}"
             onerror="this.src='/static/img/default.png'"
             style="width:60px;height:60px;object-fit:cover;border-radius:5px;">
      </div>

      <div class="flex-grow-1">
        <strong>${prod.nombre}</strong><br>
        <small>SKU: ${prod.sku} | Stock: ${prod.stock}</small>
      </div>

      <input type="checkbox"
        class="form-check-input producto-checkbox d-none"
        value="${prod.producto_id}">
    `;

    contenedor.appendChild(div);
  });

  inicializarSeleccion();
}

// selección estilo productos
function inicializarSeleccion() {
  document.querySelectorAll(".producto-item").forEach((item) => {
    const checkbox = item.querySelector(".producto-checkbox");
    const id = checkbox.value;

    item.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      item.classList.toggle("seleccionado", checkbox.checked);

      if (checkbox.checked) {
        inventarioSeleccionadoGlobal[id] = {
          nombre: item.querySelector("strong").textContent,
          sku: item.querySelector("small").textContent,
          stock: item.querySelector("small").textContent,
        };
      } else {
        delete inventarioSeleccionadoGlobal[id];
      }
    });
  });
}

// abrir modal
document.getElementById("toggleDropdownPanel").addEventListener("click", () => {
  const modal = new bootstrap.Modal(document.getElementById("modalregis"));
  modal.show();
});

// agregar a tabla
document
  .getElementById("guardarProductosSeleccionados")
  .addEventListener("click", () => {
    const tbody = document.getElementById("tablaTraslados");

    Object.entries(inventarioSeleccionadoGlobal).forEach(([id, data]) => {
      // evitar duplicados
      if (document.querySelector(`#traslado-${id}`)) return;

      const tr = document.createElement("tr");
      tr.id = `traslado-${id}`;

      tr.innerHTML = `
        <td></td>
        <td>${data.nombre}</td>
        <td>${data.sku}</td>
        <td>${data.stock}</td>
        <td>
          <input type="number"
                 class="form-control cantidad-final"
                 min="1"
                 max="${data.stock}"
                 value="1">
        </td>
        <td>
          <button class="btn btn-danger btn-sm eliminar-traslado">
            <i class="bx bx-trash"></i>
          </button>
        </td>
      `;

      tbody.appendChild(tr);
    });

    // cerrar modal correctamente (sin errores de instance null)
    const modalEl = document.getElementById("modalregis");
    const modal =
      bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);

    modal.hide();

    // limpiar backdrop si se queda pegado
    setTimeout(() => {
      document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
      document.body.classList.remove("modal-open");
      document.body.style = "";
    }, 300);

    reordenar();
  });

// eliminar
document.getElementById("tablaTraslados").addEventListener("click", (e) => {
  const btn = e.target.closest(".eliminar-traslado");
  if (!btn) return;

  const tr = btn.closest("tr");
  delete inventarioSeleccionadoGlobal[tr.id.replace("traslado-", "")];
  tr.remove();

  reordenar();
});

// orden
function reordenar() {
  document.querySelectorAll("#tablaTraslados tr").forEach((tr, i) => {
    tr.children[0].textContent = i + 1;
  });
}
