let inventarioSeleccionadoGlobal = {};
let trasladoPreviewArray = [];
const TRASLADO_PAGE_SIZE = 10;

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
      await cargarInventarioEnModal(item.dataset.value);
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });
}

/*========================================
=          FETCH UBICACIONES             =
========================================*/
async function fetchUbicaciones(term, optionsContainer) {
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

    optionsContainer.innerHTML += `
      <div class="list-group-item active bg-light text-dark fw-bold">
        ${term ? "Resultados encontrados" : "Sugerencias recientes"}
      </div>
    `;

    data.forEach((u) => {
      // =========================
      // TIPO LABEL
      // =========================
      let tipoLabel = "";

      if (u.es_bodega) {
        tipoLabel = "Bodega";
      } else if (u.es_tienda) {
        tipoLabel = "Tienda";
      } else {
        tipoLabel = "Sin tipo";
      }

      // =========================
      // TEXTO FINAL
      // =========================
      const texto = `${u.nombre}${u.codigo ? " | " + u.codigo : ""} | ${tipoLabel}`;

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

initDropdown("ubicacion_origen", fetchUbicaciones);
initDropdown("ubicacion_destino", fetchUbicaciones);

/*========================================
=       CARGAR INVENTARIO EN MODAL       =
========================================*/
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

      <div class="flex-grow-1 datos-producto"
           data-sku="${prod.sku}"
           data-stock="${prod.stock}">
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

/*========================================
=         SELECCIONAR PRODUCTOS          =
========================================*/
function inicializarSeleccion() {
  document.querySelectorAll(".producto-item").forEach((item) => {
    const checkbox = item.querySelector(".producto-checkbox");
    const id = checkbox.value;

    item.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      item.classList.toggle("seleccionado", checkbox.checked);

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

  for (let i = 1; i <= totalPaginas; i++) {
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
      const cantidad = parseFloat(fila.querySelector(".cantidad-final").value);
      const stockDisponible = parseFloat(fila.children[3].textContent);

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

      const stock = parseFloat(row.children[3].textContent) || 0;

      // 🔥 SOLO validar mientras escribe (sin forzar mínimo)
      input.addEventListener("input", () => {
        let valor = parseFloat(input.value);

        // si está vacío, no hacemos nada
        if (input.value === "") return;

        if (valor > stock) {
          input.value = stock;
        }

        if (valor < 0) {
          input.value = "";
        }
      });

      // 🔥 aquí sí corregimos el valor final
      input.addEventListener("blur", () => {
        let valor = parseFloat(input.value);

        if (isNaN(valor) || valor <= 0) {
          input.value = 1; // valor por defecto al salir
        }

        if (valor > stock) {
          input.value = stock;
        }
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
