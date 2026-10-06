let inventarioSeleccionadoGlobal = {};
let trasladoPreviewArray = [];
const TRASLADO_PAGE_SIZE = 10;
let ubicacionInventarioActual = null;
let paginaInventarioModal = 1;
let busquedaInventarioModal = "";

/*========================================
=            VALIDAR MODAL               =
========================================*/
document.getElementById("modalregis").addEventListener("show.bs.modal", (e) => {
  const origen = document.getElementById("ubicacion_origen").value;

  if (!origen) {
    e.preventDefault();

    Swal.fire({
      title: "Ubicación requerida",
      text: "Debes seleccionar una ubicación de origen antes de continuar.",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
  }
});

function formatoStockVisible(valor) {
  const numero = Number(String(valor).replace(",", "."));
  if (!Number.isFinite(numero)) return valor;
  return (Math.trunc(numero * 100) / 100).toFixed(2);
}

/*========================================
=               DEBOUNCE                 =
========================================*/
function debounce(func, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

/*========================================
=         DROPDOWN PERSONALIZADO         =
========================================*/
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
      const destinoInput = document.getElementById("ubicacion_destino");
      if (destinoInput?.value === item.dataset.value) {
        destinoInput.value = "";
        destinoInput.nextElementSibling.querySelector("button").textContent =
          "Escriba para buscar...";
      }
      await cargarInventarioEnModal(item.dataset.value);
    }
  });

  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        remoteSearchFn(searchInput.value.trim(), optionsContainer);
      }
    }, 300),
  );

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });
}

/*========================================
=          FETCH UBICACIONES             =
========================================*/
async function fetchUbicaciones(term, optionsContainer, excluirOrigen = false) {
  try {
    const res = await fetch(
      `/manager/ubicaciones/search/?search=${encodeURIComponent(term)}`,
    );

    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
      optionsContainer.innerHTML = `
        <div class="list-group-item text-muted">Sin resultados</div>
      `;
      return;
    }

    const origenSeleccionado = document.getElementById("ubicacion_origen")?.value;
    const ubicaciones = excluirOrigen
      ? data.filter((u) => String(u.id) !== String(origenSeleccionado || ""))
      : data;

    if (!ubicaciones.length) {
      optionsContainer.innerHTML = `
        <div class="list-group-item text-muted">No hay ubicaciones disponibles</div>
      `;
      return;
    }

    optionsContainer.innerHTML += `
      <div class="list-group-item active bg-light text-dark fw-bold">
        ${term ? "Resultados encontrados" : "Más utilizadas"}
      </div>
    `;

    ubicaciones.forEach((u) => {
      // El selector muestra únicamente el nombre de la ubicación.
      const texto = u.nombre;

      optionsContainer.innerHTML += `
        <button type="button"
                class="list-group-item list-group-item-action"
                data-value="${u.id}"
                data-label="${texto}">
          ${texto}
        </button>
      `;
    });
  } catch (error) {
    optionsContainer.innerHTML = `
      <div class="list-group-item text-danger">
        Error al cargar ubicaciones
      </div>
    `;
    console.error(error);
  }
}

initDropdown("ubicacion_origen", (term, contenedor) =>
  fetchUbicaciones(term, contenedor),
);
initDropdown("ubicacion_destino", (term, contenedor) =>
  fetchUbicaciones(term, contenedor, true),
);

/*========================================
=       CARGAR INVENTARIO EN MODAL       =
========================================*/
async function cargarInventarioEnModal(ubicacionId, pagina = 1, busqueda = "") {
  const contenedor = document.getElementById("contenedorProductosAjax");

  contenedor.innerHTML = `
    <div class="text-center py-4">
      Cargando...
    </div>
  `;

  if (String(ubicacionInventarioActual) !== String(ubicacionId)) {
    inventarioSeleccionadoGlobal = {};
    ubicacionInventarioActual = ubicacionId;
  }
  paginaInventarioModal = pagina;
  busquedaInventarioModal = busqueda;
  const params = new URLSearchParams({ page: pagina, limit: 10 });
  if (busqueda) params.set("search", busqueda);
  const res = await fetch(`/manager/inventario/ubicacion/${ubicacionId}/?${params}`);
  if (!res.ok) throw new Error("No se pudo cargar el inventario");
  const data = await res.json();

  contenedor.innerHTML = "";

  data.results.forEach((prod) => {

    const div = document.createElement("div");

    div.className = "productosstyle producto-item compras-product-option";

    const imagen = prod.imagen;

    div.innerHTML = `
      <img class="compras-product-option__image" src="${imagen || '/static/img/default.webp'}" alt="" onerror="this.src='/static/img/default.webp'">
      <div class="compras-product-option__info datos-producto" data-sku="${prod.sku}" data-stock="${prod.stock}">
        <strong>${prod.nombre}</strong>
        <small>SKU: ${prod.sku} · Existencias: ${formatoStockVisible(prod.stock)}</small>
      </div>
      <span class="compras-product-option__action"><i class="bx bx-plus-circle"></i> Seleccionar</span>
      <input type="checkbox" class="form-check-input producto-checkbox d-none" value="${prod.producto_id}">
    `;

    contenedor.appendChild(div);
  });

  inicializarSeleccion();
  renderPaginacionInventarioModal(data.page, data.totalPages, ubicacionId);
}

function renderPaginacionInventarioModal(pagina, totalPaginas, ubicacionId) {
  const paginador = document.getElementById("paginacionProductos");
  if (!paginador) return;
  paginador.replaceChildren();
  if (totalPaginas <= 1) return;
  const crearBoton = (texto, destino, deshabilitado, activo = false) => {
    const item = document.createElement("li");
    item.className = `page-item${deshabilitado ? " disabled" : ""}${activo ? " active" : ""}`;
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "page-link";
    boton.textContent = texto;
    boton.disabled = deshabilitado;
    boton.addEventListener("click", () => cargarInventarioEnModal(ubicacionId, destino, busquedaInventarioModal));
    item.appendChild(boton);
    paginador.appendChild(item);
  };
  crearBoton("«", pagina - 1, pagina === 1);
  for (let p = Math.max(1, pagina - 2); p <= Math.min(totalPaginas, pagina + 2); p += 1) {
    crearBoton(String(p), p, false, p === pagina);
  }
  crearBoton("»", pagina + 1, pagina === totalPaginas);
}

/*========================================
=         SELECCIONAR PRODUCTOS          =
========================================*/
function inicializarSeleccion() {
  document.querySelectorAll(".producto-item").forEach((item) => {
    const checkbox = item.querySelector(".producto-checkbox");
    const id = checkbox.value;
    const actualizarEtiqueta = () => {
      const etiqueta = item.querySelector(".compras-product-option__action");
      etiqueta.innerHTML = checkbox.checked
        ? '<i class="bx bx-check-circle"></i> Seleccionado'
        : '<i class="bx bx-plus-circle"></i> Seleccionar';
    };

    if (inventarioSeleccionadoGlobal[id]) {
      checkbox.checked = true;
      item.classList.add("seleccionado");
    }
    actualizarEtiqueta();

    item.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      item.classList.toggle("seleccionado", checkbox.checked);
      actualizarEtiqueta();

      if (checkbox.checked) {
        const datos = item.querySelector(".datos-producto");

        inventarioSeleccionadoGlobal[id] = {
          nombre: item.querySelector("strong").textContent,
          sku: datos.dataset.sku,
          stock: datos.dataset.stock,
        };
      } else {
        delete inventarioSeleccionadoGlobal[id];
      }
    });
  });
}

/*========================================
=           ABRIR MODAL                  =
========================================*/
document.getElementById("toggleDropdownPanel").addEventListener("click", () => {
  const modal = new bootstrap.Modal(document.getElementById("modalregis"));
  modal.show();
});

document.getElementById("formBuscarProductosCompra")?.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!ubicacionInventarioActual) return;
  const busqueda = document.getElementById("buscadorProductos")?.value.trim() || "";
  cargarInventarioEnModal(ubicacionInventarioActual, 1, busqueda);
});

/*========================================
=        GUARDAR PRODUCTOS A TABLA       =
========================================*/
document
  .getElementById("guardarProductosSeleccionados")
  .addEventListener("click", () => {
    const tbody = document.getElementById("tablaTraslados");

    Object.entries(inventarioSeleccionadoGlobal).forEach(([id, data]) => {
      if (document.querySelector(`#traslado-${id}`)) return;

      const tr = document.createElement("tr");
      tr.id = `traslado-${id}`;
      tr.dataset.stock = data.stock;

      tr.innerHTML = `
        <td></td>
        <td>${data.nombre}</td>
        <td>${data.sku}</td>
        <td>${formatoStockVisible(data.stock)}</td>
        <td>
          <input type="number"
                 class="form-control cantidad-final"
                 min="1"
                 max="${Math.floor(Number(data.stock))}"
                 step="1"
                 inputmode="numeric"
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

    const modalEl = document.getElementById("modalregis");
    const modal =
      bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);

    modal.hide();

    setTimeout(() => {
      document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
      document.body.classList.remove("modal-open");
      document.body.style = "";
    }, 300);

    reordenar();
  });

/*========================================
=         ELIMINAR DE TABLA              =
========================================*/
document.getElementById("tablaTraslados").addEventListener("click", (e) => {
  const btn = e.target.closest(".eliminar-traslado");
  if (!btn) return;

  const tr = btn.closest("tr");
  delete inventarioSeleccionadoGlobal[tr.id.replace("traslado-", "")];
  tr.remove();

  reordenar();
});

/*========================================
=             REORDENAR                  =
========================================*/
function reordenar() {
  document.querySelectorAll("#tablaTraslados tr").forEach((tr, i) => {
    tr.children[0].textContent = i + 1;
  });
}

/*========================================
=           PREVIEW TRASLADO             =
========================================*/
document.getElementById("btnPreviewTraslado").addEventListener("click", () => {
  const origenId = document.getElementById("ubicacion_origen").value;
  const destinoId = document.getElementById("ubicacion_destino").value;
  const filas = document.querySelectorAll("#tablaTraslados tr");

  let errores = [];

  if (!origenId) errores.push("Debe seleccionar una ubicación de origen.");
  if (!destinoId) errores.push("Debe seleccionar una ubicación destino.");
  if (filas.length === 0)
    errores.push("Debe agregar al menos un producto para trasladar.");

  if (errores.length > 0) {
    Swal.fire({
      title: "Datos incompletos",
      html: errores.join("<br>"),
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }

  document.getElementById("previewOrigen").value = document
    .getElementById("ubicacion_origen")
    .nextElementSibling.querySelector("button").textContent;

  document.getElementById("previewDestino").value = document
    .getElementById("ubicacion_destino")
    .nextElementSibling.querySelector("button").textContent;

  trasladoPreviewArray = Array.from(filas).map((fila) => ({
    producto: fila.children[1].textContent,
    sku: fila.children[2].textContent,
    stock: fila.children[3].textContent,
    cantidad: fila.querySelector(".cantidad-final").value,
  }));

  mostrarPaginaPreviewTraslado(1);

  const modal = bootstrap.Modal.getOrCreateInstance(
    document.getElementById("completartraslado"),
  );
  modal.show();
});

function mostrarPaginaPreviewTraslado(pagina = 1) {
  const tbody = document.getElementById("tablaPreviewTraslado");
  const paginador = document.getElementById("paginadorPreviewTraslado");

  tbody.innerHTML = "";
  paginador.innerHTML = "";

  const inicio = (pagina - 1) * TRASLADO_PAGE_SIZE;
  const fin = inicio + TRASLADO_PAGE_SIZE;

  const itemsPagina = trasladoPreviewArray.slice(inicio, fin);

  itemsPagina.forEach((item, index) => {
    tbody.innerHTML += `
      <tr>
        <td>${inicio + index + 1}</td>
        <td>${item.producto}</td>
        <td>${item.sku}</td>
        <td>${item.stock}</td>
        <td>${item.cantidad}</td>
      </tr>
    `;
  });

  const totalPaginas = Math.ceil(
    trasladoPreviewArray.length / TRASLADO_PAGE_SIZE,
  );

  if (totalPaginas <= 1) return;

  const inicioPagina = Math.max(1, pagina - 2);
  const finPagina = Math.min(totalPaginas, pagina + 2);
  for (let i = inicioPagina; i <= finPagina; i++) {
    paginador.innerHTML += `
      <button type="button"
              class="btn btn-sm ${i === pagina ? "classbotones" : "btn-light"} me-1"
              onclick="mostrarPaginaPreviewTraslado(${i})">
        ${i}
      </button>
    `;
  }
}

document
  .getElementById("confirmarTrasladoBtn")
  .addEventListener("click", async function () {
    const origenId = parseInt(
      document.getElementById("ubicacion_origen").value,
    );
    const destinoId = parseInt(
      document.getElementById("ubicacion_destino").value,
    );
    const observaciones = document
      .getElementById("observacionesTraslado")
      .value.trim();

    const detalles = [];

    document.querySelectorAll("#tablaTraslados tr").forEach((fila) => {
      const productoId = parseInt(fila.id.replace("traslado-", ""));
      const cantidad = parseInt(fila.querySelector(".cantidad-final").value, 10);
      const stockDisponible = parseFloat(fila.dataset.stock || fila.children[3].textContent);

      detalles.push({
        productoId,
        cantidad,
        stockDisponible,
      });
    });

    const payload = {
      origenId,
      destinoId,
      observaciones,
      detalles,
    };

    try {
      const response = await fetch("/manager/traslados/post/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        Swal.fire({
          title: "¡Éxito!",
          text: data.message || "Traslado registrado correctamente.",
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        }).then(() => {
          window.location.href = "/manager/traslados/";
        });
      } else {
        throw new Error(data.message || "Error al registrar traslado.");
      }
    } catch (err) {
      Swal.fire({
        title: "Error",
        text: err.message,
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  });

document.addEventListener("DOMContentLoaded", () => {
  function validarCantidadesTraslado() {
    const rows = document.querySelectorAll("#tablaTraslados tr");

    rows.forEach((row) => {
      const input = row.querySelector(".cantidad-final");
      if (!input) return;
      if (input.dataset.trasladoValidado) return;
      input.dataset.trasladoValidado = "true";

      const stock = parseFloat(row.dataset.stock || row.children[3].textContent) || 0;
      const maximoEntero = Math.floor(stock);

      const normalizarCantidad = (usarMinimo = false) => {
        if (input.value === "") {
          if (usarMinimo) input.value = "1";
          return;
        }
        let valor = Math.trunc(Number(input.value));
        if (!Number.isFinite(valor) || valor < 1) {
          input.value = usarMinimo ? "1" : "";
          return;
        }
        if (valor > maximoEntero) valor = maximoEntero;
        input.value = String(valor);
      };

      input.addEventListener("input", () => {
        normalizarCantidad(false);
      });

      input.addEventListener("blur", () => {
        normalizarCantidad(true);
      });
    });
  }

  document
    .getElementById("guardarProductosSeleccionados")
    .addEventListener("click", () => {
      setTimeout(validarCantidadesTraslado, 100);
    });

  validarCantidadesTraslado();
});
