let modalDetallesArray = [];
const MODAL_PAGE_SIZE = 10;

//----------------
// INPUT SELECT SMART SEARCH
//----------------

// Función debounce
function debounce(func, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

// Inicialización genérica del dropdown
function initDropdown(hiddenInputId, remoteSearchFn = null) {
  const hiddenInput = document.getElementById(hiddenInputId);
  const container = hiddenInput.nextElementSibling;
  const selectBtn = container.querySelector("button");
  const dropdown = container.querySelector(".dropdown-menu");
  const searchInput = container.querySelector(".search-box input");
  const optionsContainer = container.querySelector(".options");

  // Seleccionar opción
  optionsContainer.addEventListener("click", (e) => {
    const item = e.target.closest(".list-group-item");
    if (item) {
      hiddenInput.value = item.dataset.value;
      hiddenInput.dataset.saldo = item.dataset.saldo || "0";
      selectBtn.textContent = item.dataset.label;
      dropdown.classList.remove("show");
      searchInput.value = "";
    }
  });

  // Abrir dropdown y cargar sugerencias
  selectBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("show");
    searchInput.focus();

    if (dropdown.classList.contains("show") && remoteSearchFn) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Cargando sugerencias...</div>
            `;
      await remoteSearchFn("", optionsContainer);
    }
  });

  // Buscar mientras escribe
  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Buscando...</div>
            `;
        remoteSearchFn(searchInput.value.trim(), optionsContainer);
      }
    }, 300),
  );

  // Cerrar al hacer click fuera
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });

  return { hiddenInput, selectBtn, optionsContainer };
}

//----------------
// FETCH PROVEEDORES
//----------------
async function fetchProveedores(term, optionsContainer) {
  try {
    const res = await fetch(
      `/manager/proveedores/search/?search=${encodeURIComponent(term)}`,
    );
    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Sin resultados</div>
            `;
      return;
    }

    // Encabezado visual
    optionsContainer.innerHTML += `
            <div class="list-group-item active bg-light text-dark fw-bold">
                ${term ? "Resultados encontrados" : "Más utilizados"}
            </div>
        `;

    data.forEach((p) => {
      const texto = p.nombreLegal;

      optionsContainer.innerHTML += `
                <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${p.id}"
                        data-label="${texto}"
                        data-saldo="${p.saldo || 0}">
                     ${texto}
                </button>
            `;
    });
  } catch (error) {
    optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">Error al cargar proveedores</div>
        `;
    console.error(error);
  }
}

//----------------
// FETCH UBICACIONES
//----------------
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
        ${term ? "Resultados encontrados" : "Más utilizadas"}
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
      const texto = `${u.nombre} | ${tipoLabel}`;

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

//----------------
// INICIALIZAR COMPONENTES
//----------------
initDropdown("proveedoresid", fetchProveedores);
initDropdown("recepcionid", fetchUbicaciones);

function actualizarOpcionCredito(diasCredito) {
  const tipoCompra = document.getElementById("tcompra");
  const opcionCredito = tipoCompra?.querySelector('option[value="2"]');
  if (!opcionCredito) return; // El permiso sigue controlando si la opción existe.

  const creditoDisponible = Number(diasCredito) > 0;
  opcionCredito.hidden = !creditoDisponible;
  opcionCredito.disabled = !creditoDisponible;

  if (!creditoDisponible && tipoCompra.value === "2") {
    tipoCompra.value = "1";
  }
}

function actualizarVisibilidadSaldoUsado(mostrar) {
  document.querySelectorAll(".saldo-usado-col").forEach((celda) => {
    celda.classList.toggle("d-none", !mostrar);
  });
}

function importesCompra(precio, cantidad, impuesto) {
  const subtotal = precio * cantidad;
  const impuestoUnitario = Math.round((precio * (impuesto / 100) + Number.EPSILON) * 100) / 100;
  const totalImpuesto = impuestoUnitario * cantidad;
  return {
    subtotal,
    impuestoUnitario,
    totalImpuesto,
    total: subtotal + totalImpuesto,
  };
}

/*---------------------------------------------------------------*/
//--------------
// llenar modal envio
//--------------
document
  .getElementById("toggleDropdownPanel32")
  .addEventListener("click", async function () {
    const proveedorId = document.getElementById("proveedoresid").value;
    const productosSeleccionados = document.querySelectorAll(
      "#tablacont tbody tr",
    );
    const recepcionId = document.getElementById("recepcionid").value;

    let errores = [];

    if (!proveedorId) errores.push("Debe seleccionar un proveedor.");
    if (productosSeleccionados.length === 0)
      errores.push("Debe agregar al menos un producto.");

    if (!recepcionId)
      errores.push("Debe seleccionar una ubicación de recepción.");

    productosSeleccionados.forEach((fila, index) => {
      const precio = fila.querySelector(".precio-input").value.trim();
      const impuesto = fila.querySelector(".impuesto-input").value.trim();
      const cantidad = fila.querySelector(".cantidad-input").value.trim();

      if (!precio || isNaN(precio) || parseFloat(precio) <= 0)
        errores.push(`Precio inválido en el producto #${index + 1}`);
      if (!cantidad || isNaN(cantidad) || parseInt(cantidad) <= 0)
        errores.push(`Cantidad inválida en el producto #${index + 1}`);
      if (impuesto === "" || isNaN(impuesto) || parseFloat(impuesto) < 0 || parseFloat(impuesto) > 100)
        errores.push(`Impuesto inválido en el producto #${index + 1}`);
    });

    if (errores.length > 0) {
      Swal.fire({
        title: "Campos incompletos",
        html: errores.join("<br>"),
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

    // Construir modalDetallesArray
    modalDetallesArray = Array.from(productosSeleccionados).map((fila) => {
      const precio = parseFloat(fila.querySelector(".precio-input").value);
      const cantidad = parseInt(fila.querySelector(".cantidad-input").value);
      const impuesto = parseFloat(fila.querySelector(".impuesto-input").value) || 0;
      return {
        nombre: fila.children[1].textContent,
        presentacion: fila.children[2].textContent,
        sku: fila.children[3].textContent,
        precio,
        cantidad,
        impuesto,
        ...importesCompra(precio, cantidad, impuesto),
      };
    });

    // Llamar al paginador para llenar el modal
    mostrarPaginaComprar(1);

    let saldoProveedor = Number(
      document.getElementById("proveedoresid").dataset.saldo || 0,
    );
    let diasCreditoProveedor = 0;
    try {
      const respuestaProveedor = await fetch(
        `/manager/proveedores/get/${proveedorId}/`,
      );
      const datosProveedor = await respuestaProveedor.json();
      if (respuestaProveedor.ok) {
        saldoProveedor = Number(datosProveedor.proveedor?.saldo || 0);
        diasCreditoProveedor = Number(
          datosProveedor.proveedor?.dias_credito || 0,
        );
      }
    } catch (_) {
      /* Se conserva el último saldo conocido para no bloquear la compra. */
    }
    actualizarOpcionCredito(diasCreditoProveedor);
    const contenedorSaldo = document.getElementById(
      "contenedorUsarSaldoProveedor",
    );
    const checkSaldo = document.getElementById("usarSaldoProveedor");
    checkSaldo.checked = false;
    contenedorSaldo.classList.toggle("d-none", saldoProveedor <= 0);
    document.getElementById("saldoProveedorDisponible").textContent =
      `L. ${saldoProveedor.toFixed(2)}`;
    const subtotalModal = modalDetallesArray.reduce(
      (acumulado, item) => acumulado + item.subtotal,
      0,
    );
    const impuestoModal = modalDetallesArray.reduce(
      (acumulado, item) => acumulado + item.totalImpuesto,
      0,
    );
    const totalConImpuesto = subtotalModal + impuestoModal;
    const actualizarResumenSaldo = () => {
      const aplicado = checkSaldo.checked
        ? Math.min(saldoProveedor, totalConImpuesto)
        : 0;
      const pendiente = totalConImpuesto - aplicado;
      actualizarVisibilidadSaldoUsado(checkSaldo.checked);
      document.getElementById("subtotalModalCompra").textContent =
        `L. ${subtotalModal.toFixed(2)}`;
      document.getElementById("impuestoModalCompra").textContent =
        `L. ${impuestoModal.toFixed(2)}`;
      document.getElementById("saldoUsadoModalCompra").textContent =
        `L. ${aplicado.toFixed(2)}`;
      document.getElementById("totalModalCompra").textContent =
        `L. ${totalConImpuesto.toFixed(2)}`;
      document.getElementById("totalPagarModalCompra").textContent =
        `L. ${pendiente.toFixed(2)}`;
    };
    checkSaldo.onchange = actualizarResumenSaldo;
    actualizarResumenSaldo();

    // Abrir modal
    const modalElement = document.getElementById("completarcompra");
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
  });

function mostrarPaginaComprar(page = 1) {
  const tablaModal = document.getElementById("tablaDetallesModal");
  const pagDiv = document.getElementById("paginadorcomprar");

  const totalItems = modalDetallesArray.length;
  const totalPages = Math.ceil(totalItems / MODAL_PAGE_SIZE) || 1;
  page = Math.max(1, Math.min(page, totalPages));

  const start = (page - 1) * MODAL_PAGE_SIZE;
  const end = start + MODAL_PAGE_SIZE;
  const items = modalDetallesArray.slice(start, end);
  const mostrarSaldoUsado =
    document.getElementById("usarSaldoProveedor")?.checked || false;

  tablaModal.innerHTML = "";
  items.forEach((prod, idx) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
            <td>${start + idx + 1}</td>
            <td>${prod.nombre}</td>
            <td>${prod.presentacion}</td>
            <td>${prod.sku}</td>
            <td>${prod.cantidad}</td>
            <td>L. ${prod.precio.toFixed(2)}</td>
            <td>${prod.impuesto.toFixed(2)}%</td>
            <td>L. ${prod.impuestoUnitario.toFixed(2)}</td>
            <td>L. ${prod.subtotal.toFixed(2)}</td>
            <td class="saldo-usado-col${mostrarSaldoUsado ? "" : " d-none"}"></td>
            <td>L. ${prod.total.toFixed(2)}</td>
        `;
    tablaModal.appendChild(tr);
  });

  // Paginación
  pagDiv.innerHTML = "";
  const ul = document.createElement("ul");
  ul.className = "pagination";

  const crearLi = (text, disabled, onclick) => {
    const li = document.createElement("li");
    li.className = "page-item" + (disabled ? " disabled" : "");
    li.innerHTML = `<button type="button" class="page-link">${text}</button>`;
    if (!disabled)
      li.addEventListener("click", (e) => {
        e.preventDefault();
        onclick();
      });
    return li;
  };

  ul.appendChild(
    crearLi("«", page === 1, () => mostrarPaginaComprar(page - 1)),
  );
  const inicioPagina = Math.max(1, page - 2);
  const finPagina = Math.min(totalPages, page + 2);
  for (let p = inicioPagina; p <= finPagina; p++) {
    const li = document.createElement("li");
    li.className = "page-item" + (p === page ? " active" : "");
    li.innerHTML = `<button type="button" class="page-link">${p}</button>`;
    li.addEventListener("click", (e) => {
      e.preventDefault();
      mostrarPaginaComprar(p);
    });
    ul.appendChild(li);
  }
  ul.appendChild(
    crearLi("»", page === totalPages, () => mostrarPaginaComprar(page + 1)),
  );

  pagDiv.appendChild(ul);
}

//--------------
// ENVIAR
//--------------
document
  .getElementById("enviarCompraBtn")
  .addEventListener("click", async function () {
    const proveedorInput = document.getElementById("proveedoresid");
    if (!proveedorInput) {
      Swal.fire({
        title: "Error",
        text: "No se encontró el campo de proveedor en el formulario.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

    const recepcionInput = document.getElementById("recepcionid");
    if (!recepcionInput) {
      Swal.fire({
        title: "Error",
        text: "No se encontró el campo de ubicación de recepción en el formulario.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const recepcionId = parseInt(recepcionInput.value);
    const proveedorId = parseInt(proveedorInput.value);
    const tipoCompraValue = parseInt(document.getElementById("tcompra").value);
    const observaciones = document.getElementById("observaciones").value.trim();
    const usarSaldo =
      document.getElementById("usarSaldoProveedor")?.checked || false;
    if (!tipoCompraValue) {
      Swal.fire({
        title: "Error",
        text: "Tipo de compra en requerido.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const detalles = [];

    document.querySelectorAll("#tablacont tbody tr").forEach((fila) => {
      const productoId = parseInt(fila.id.replace("producto-row-", ""));
      const cantidad = parseInt(fila.querySelector(".cantidad-input").value);
      const precioCompra = parseFloat(
        fila.querySelector(".precio-input").value,
      );
      const impuesto = parseFloat(fila.querySelector(".impuesto-input").value) || 0;

      detalles.push({ productoId, cantidad, precioCompra, impuesto });
    });

    const payload = {
      proveedorId,
      recepcionId,
      tipoCompra: tipoCompraValue,
      observaciones,
      usarSaldo,
      detalles,
    };

    try {
      const response = await fetch("/manager/compras/realizarcompra/post/", {
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
          text: data.message || "Compra registrada correctamente.",
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        }).then(() => (window.location.href = "/manager/compras/"));
      } else {
        throw new Error(data.message || "Error al registrar la compra.");
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

/*---------------------------------------------------------------------*/

let productosSeleccionadosGlobal = {};
const PRODUCTOS_POR_PAGINA = 10;
let paginaTablaCompra =
  Math.max(1, Number(new URLSearchParams(window.location.search).get("page"))) || 1;

function urlPaginaCompra(pagina) {
  const url = new URL(window.location.href);
  url.searchParams.set("page", pagina);
  return `${url.pathname}${url.search}${url.hash}`;
}

function actualizarUrlPaginaCompra() {
  window.history.replaceState({}, "", urlPaginaCompra(paginaTablaCompra));
}

document.addEventListener("DOMContentLoaded", () => {
  const buscador = document.getElementById("buscadorProductos");

  cargarProductos();

  buscador.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      cargarProductos(1, buscador.value.trim());
    }
  });

  document
    .getElementById("formBuscarProductosCompra")
    .addEventListener("submit", (event) => {
      event.preventDefault();
      cargarProductos(1, buscador.value.trim());
    });

  document
    .getElementById("guardarProductosSeleccionados")
    .addEventListener("click", () => {
      agregarProductosSeleccionados();
    });

  document.querySelector("#tablacont").addEventListener("click", function (e) {
    const boton = e.target.closest(".eliminar-fila");
    if (!boton) return;

    const fila = boton.closest("tr");
    if (!fila) return;

    const idProducto = fila.id.replace("producto-row-", "");
    fila.remove();

    // Eliminar también del estado global
    delete productosSeleccionadosGlobal[idProducto];

    // Deseleccionar en el modal
    const checkbox = document.querySelector(
      `.producto-checkbox[value="${idProducto}"]`,
    );
    if (checkbox) {
      checkbox.checked = false;
      const productoItem = checkbox.closest(".producto-item");
      if (productoItem) {
        productoItem.classList.remove("seleccionado");
      }
    }

    reordenarTabla();
    actualizarPaginacionTablaCompra();
    actualizarTotales();
  });
});

async function cargarProductos(page = 1, search = "") {
  const contenedor = document.getElementById("contenedorProductosAjax");
  const paginacion = document.getElementById("paginacionProductos");

  let loadingDiv = contenedor.querySelector("#loadingProductos");
  if (!loadingDiv) {
    loadingDiv = document.createElement("div");
    loadingDiv.id = "loadingProductos";
    loadingDiv.className = "text-center py-4";
    loadingDiv.textContent = "Cargando productos...";
    contenedor.prepend(loadingDiv);
  }
  loadingDiv.style.display = "block";
  paginacion.innerHTML = "";

  try {
    // Llamada al proxy en tu servidor Django
    const url = new URL(
      `/manager/api/proxy/productos/`,
      window.location.origin,
    );
    url.searchParams.append("page", page);
    url.searchParams.append("limit", 10);
    if (search) url.searchParams.append("search", search);

    const response = await fetch(url);
    if (!response.ok) throw new Error("Error al obtener productos");

    const data = await response.json();
    loadingDiv.style.display = "none";

    let productosDiv = contenedor.querySelector("#productos-lista");
    if (!productosDiv) {
      productosDiv = document.createElement("div");
      productosDiv.id = "productos-lista";
      productosDiv.style.maxHeight = "400px";
      productosDiv.style.overflowY = "auto";
      contenedor.appendChild(productosDiv);
    }
    productosDiv.innerHTML = "";

    data.results.forEach((prod) => {
      const div = document.createElement("div");
      const presentacion =
        prod.unidadMedida?.abreviatura || prod.unidadMedida?.nombre || "N/A";
      div.className = "productosstyle producto-item compras-product-option";
      div.dataset.id = prod.id;
      div.dataset.nombre = prod.nombre.toLowerCase();
      div.dataset.presentacion = presentacion;
      div.dataset.sku = prod.codigoSKU.toLowerCase();

      div.innerHTML = `
                <img class="compras-product-option__image" src="${prod.imagenUrl}" alt="" onerror="this.src='/static/img/default.webp'">
                <div class="compras-product-option__info">
                    <strong>${prod.nombre}</strong>
                    <small>${presentacion} · SKU: ${prod.codigoSKU}</small>
                </div>
                <span class="compras-product-option__action"><i class="bx bx-plus-circle"></i> Seleccionar</span>
                <input type="checkbox" class="form-check-input producto-checkbox d-none" value="${prod.id}">
            `;

      productosDiv.appendChild(div);
    });

    renderPaginacion(data.page, data.totalPages, search);
  } catch (error) {
    loadingDiv.style.display = "none";
    contenedor.innerHTML = `<p class="text-danger text-center py-4">${error.message}</p>`;
  }

  inicializarSeleccionProductos();
}

function inicializarSeleccionProductos() {
  document.querySelectorAll(".producto-item").forEach((prod) => {
    const checkbox = prod.querySelector(".producto-checkbox");
    const id = checkbox.value;
    const actualizarEtiqueta = () => {
      const etiqueta = prod.querySelector(".compras-product-option__action");
      etiqueta.innerHTML = checkbox.checked
        ? '<i class="bx bx-check-circle"></i> Seleccionado'
        : '<i class="bx bx-plus-circle"></i> Seleccionar';
    };

    // Restaurar selección desde el global
    if (productosSeleccionadosGlobal[id]) {
      checkbox.checked = true;
      prod.classList.add("seleccionado");
    }
    actualizarEtiqueta();

    prod.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      prod.classList.toggle("seleccionado", checkbox.checked);
      actualizarEtiqueta();

      if (checkbox.checked) {
        productosSeleccionadosGlobal[id] = {
          nombre: prod.dataset.nombre,
          presentacion: prod.dataset.presentacion,
          sku: prod.dataset.sku,
        };
      } else {
        delete productosSeleccionadosGlobal[id];
      }
    });
  });
}

function renderPaginacion(currentPage, totalPages, search) {
  const paginacion = document.getElementById("paginacionProductos");
  paginacion.innerHTML = "";

  const startPage = Math.max(currentPage - 2, 1);
  const endPage = Math.min(totalPages, currentPage + 2);

  const liPrev = document.createElement("li");
  liPrev.classList.add("page-item");
  if (currentPage === 1) liPrev.classList.add("disabled");
  liPrev.innerHTML = `<button type="button" class="page-link">«</button>`;
  liPrev.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage > 1) cargarProductos(currentPage - 1, search);
  });
  paginacion.appendChild(liPrev);

  for (let p = startPage; p <= endPage; p++) {
    const li = document.createElement("li");
    li.classList.add("page-item");
    if (p === currentPage) li.classList.add("active");
    li.innerHTML = `<button type="button" class="page-link">${p}</button>`;
    li.addEventListener("click", (e) => {
      e.preventDefault();
      if (p !== currentPage) cargarProductos(p, search);
    });
    paginacion.appendChild(li);
  }

  const liNext = document.createElement("li");
  liNext.classList.add("page-item");
  if (currentPage === totalPages) liNext.classList.add("disabled");
  liNext.innerHTML = `<button type="button" class="page-link">»</button>`;
  liNext.addEventListener("click", (e) => {
    e.preventDefault();
    if (currentPage < totalPages) cargarProductos(currentPage + 1, search);
  });
  paginacion.appendChild(liNext);
}

function agregarProductosSeleccionados() {
  const tablaBody = document.querySelector("#tablacont tbody");
  let agregados = 0;

  Object.entries(productosSeleccionadosGlobal).forEach(([id, data]) => {
    if (document.querySelector(`#producto-row-${id}`)) return;

    const fila = document.createElement("tr");
    fila.id = `producto-row-${id}`;
    fila.innerHTML = `
            <td></td>
            <td>${data.nombre}</td>
            <td>${data.presentacion}</td>
            <td>${data.sku}</td>
            <td>
                <input type="text" inputmode="decimal" class="form-control precio-input" name="precio_${id}" required>
            </td>
            <td>
                <input type="text" inputmode="decimal" class="form-control precio-input impuesto-input" name="impuesto_${id}" value="0" required>
            </td>
            <td>
                <input type="text" inputmode="numeric" class="form-control cantidad-input" name="cantidad_${id}" value="1" required>
            </td>
            <td>
                <button type="button" class="btn btn-danger btn-sm eliminar-fila">
                    <i class='bx bx-trash'></i>
                </button>
            </td>
        `;
    tablaBody.appendChild(fila);
    agregados++;
    inicializarEventosInputsTotales();
  });

  reordenarTabla();
  if (agregados) paginaTablaCompra = 1;
  actualizarPaginacionTablaCompra();
  actualizarTotales();

  const buscador = document.getElementById("buscadorProductos");
  if (buscador) buscador.value = "";
  cargarProductos(1, "");

  const modal = bootstrap.Modal.getInstance(
    document.getElementById("modalregis"),
  );
  modal.hide();
}

function reordenarTabla() {
  const tablaBody = document.querySelector("#tablacont tbody");
  if (!tablaBody) return;
  const filas = tablaBody.querySelectorAll("tr");
  filas.forEach((fila, index) => {
    const primeraCelda = fila.querySelector("td:first-child");
    if (primeraCelda) {
      primeraCelda.textContent = index + 1;
    }
  });
}

function actualizarTotales() {
  let subtotal = 0;
  let totalImpuesto = 0;
  let contador = 0;
  let cantidadTotal = 0;

  const tablaBody = document.querySelector("#tablacont tbody");
  if (!tablaBody) return;

  tablaBody.querySelectorAll("tr").forEach((fila) => {
    const precioInput = fila.querySelector("input.precio-input");
    const impuestoInput = fila.querySelector("input.impuesto-input");
    const cantidadInput = fila.querySelector("input.cantidad-input");

    const precio = parseFloat(precioInput?.value) || 0;
    const impuesto = parseFloat(impuestoInput?.value) || 0;
    const cantidad = parseInt(cantidadInput?.value) || 0;

    const importes = importesCompra(precio, cantidad, impuesto);
    subtotal += importes.subtotal;
    totalImpuesto += importes.totalImpuesto;
    contador++;
    cantidadTotal += cantidad;
  });

  document.getElementById("subtotal-compra").textContent =
    `Antes imp.: L. ${subtotal.toFixed(2)}`;
  document.getElementById("impuesto-compra").textContent =
    `Impuestos: L. ${totalImpuesto.toFixed(2)}`;
  document.getElementById("total-compra").textContent =
    `Después imp.: L. ${(subtotal + totalImpuesto).toFixed(2)}`;
  document.getElementById("contador-productos").textContent =
    `Productos: ${contador}`;
  document.getElementById("cantidad-productos").textContent =
    `Total de productos: ${cantidadTotal}`;
}

function inicializarEventosInputsTotales() {
  const tablaBody = document.querySelector("#tablacont tbody");
  if (!tablaBody) return;

  tablaBody
    .querySelectorAll("input.precio-input, input.impuesto-input, input.cantidad-input")
    .forEach((input) => {
      if (!input.dataset.compraFiltroNumerico) {
        input.addEventListener("input", () => {
          const valor = input.value;
          const limpio = input.classList.contains("cantidad-input")
            ? valor.replace(/\D/g, "")
            : valor.replace(/[^0-9.]/g, "").replace(/(\..*)\./g, "$1");

          if (valor !== limpio) input.value = limpio;
        });
        input.dataset.compraFiltroNumerico = "true";
      }
      input.removeEventListener("input", actualizarTotales);
      input.addEventListener("input", actualizarTotales);
    });
}

function actualizarPaginacionTablaCompra() {
  const tablaBody = document.querySelector("#tablacont tbody");
  const paginador = document.getElementById("paginadorProv");
  if (!tablaBody || !paginador) return;

  const filas = Array.from(tablaBody.querySelectorAll("tr"));
  const totalPaginas = Math.ceil(filas.length / PRODUCTOS_POR_PAGINA);

  if (!totalPaginas) {
    paginador.innerHTML = "";
    return;
  }

  paginaTablaCompra = Math.min(Math.max(1, paginaTablaCompra), totalPaginas);
  actualizarUrlPaginaCompra();
  filas.forEach((fila, indice) => {
    fila.hidden =
      Math.floor(indice / PRODUCTOS_POR_PAGINA) + 1 !== paginaTablaCompra;
  });

  const lista = document.createElement("ul");
  lista.className = "pagination mb-0";
  const crearBoton = (texto, pagina, deshabilitado, activo = false) => {
    const item = document.createElement("li");
    item.className = `page-item${deshabilitado ? " disabled" : ""}${activo ? " active" : ""}`;
    const boton = document.createElement("a");
    boton.className = "page-link";
    boton.textContent = texto;
    boton.href = urlPaginaCompra(Math.max(1, pagina));
    if (deshabilitado) {
      boton.setAttribute("aria-disabled", "true");
      boton.tabIndex = -1;
    }
    if (!deshabilitado && !activo) {
      boton.addEventListener("click", (event) => {
        event.preventDefault();
        paginaTablaCompra = pagina;
        actualizarPaginacionTablaCompra();
      });
    }
    item.appendChild(boton);
    lista.appendChild(item);
  };

  crearBoton("«", paginaTablaCompra - 1, paginaTablaCompra === 1);
  const inicioPagina = Math.max(1, paginaTablaCompra - 2);
  const finPagina = Math.min(totalPaginas, paginaTablaCompra + 2);
  for (let pagina = inicioPagina; pagina <= finPagina; pagina++) {
    crearBoton(String(pagina), pagina, false, pagina === paginaTablaCompra);
  }
  crearBoton("»", paginaTablaCompra + 1, paginaTablaCompra === totalPaginas);

  paginador.replaceChildren(lista);
}
