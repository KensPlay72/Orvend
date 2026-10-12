let inventarioMermaSeleccionado = {};
let ubicacionMermaActual = "";
let paginaInventarioMerma = 1;
let busquedaInventarioMerma = "";
const cacheInventarioMerma = new Map();
const cacheUbicacionesMerma = new Map();
let solicitudInventarioMerma;
let solicitudUbicacionesMerma;

const escaparHtml = (valor) =>
  String(valor ?? "").replace(/[&<>"']/g, (caracter) => {
    const entidades = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entidades[caracter];
  });

const formatoStockMerma = (valor) => {
  const numero = Number(valor);
  return Number.isFinite(numero)
    ? new Intl.NumberFormat("es-HN", { maximumFractionDigits: 6 }).format(numero)
    : String(valor);
};

async function buscarUbicaciones(term, contenedor) {
  solicitudUbicacionesMerma?.abort();
  solicitudUbicacionesMerma = new AbortController();
  const solicitud = solicitudUbicacionesMerma;
  contenedor.replaceChildren();
  const cargando = document.createElement("div");
  cargando.className = "list-group-item text-muted";
  cargando.textContent = "Cargando sucursales...";
  contenedor.appendChild(cargando);
  try {
    const cacheGuardado = cacheUbicacionesMerma.get(term);
    let ubicaciones =
      cacheGuardado && Date.now() - cacheGuardado.fecha < 30000
        ? cacheGuardado.ubicaciones
        : null;
    if (!ubicaciones) {
      const response = await fetch(
        `/manager/ubicaciones/search/?search=${encodeURIComponent(term)}`,
        { signal: solicitud.signal },
      );
      if (!response.ok) throw new Error("No se pudieron cargar las sucursales.");
      ubicaciones = await response.json();
      cacheUbicacionesMerma.set(term, { ubicaciones, fecha: Date.now() });
      if (cacheUbicacionesMerma.size > 20) {
        cacheUbicacionesMerma.delete(cacheUbicacionesMerma.keys().next().value);
      }
    }
    if (solicitud !== solicitudUbicacionesMerma) return;
    contenedor.replaceChildren();
    if (!ubicaciones.length) {
      const vacio = document.createElement("div");
      vacio.className = "list-group-item text-muted";
      vacio.textContent = "Sin sucursales encontradas";
      contenedor.appendChild(vacio);
      return;
    }
    const encabezado = document.createElement("div");
    encabezado.className = "list-group-item active bg-light text-dark fw-bold";
    encabezado.textContent = term ? "Resultados encontrados" : "Sucursales más utilizadas";
    contenedor.appendChild(encabezado);
    ubicaciones.forEach((ubicacion) => {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.className = "list-group-item list-group-item-action";
      boton.dataset.value = ubicacion.id;
      boton.dataset.label = ubicacion.nombre;
      boton.textContent = ubicacion.nombre;
      contenedor.appendChild(boton);
    });
  } catch (error) {
    if (error.name !== "AbortError" && solicitud === solicitudUbicacionesMerma) {
      contenedor.replaceChildren();
      const aviso = document.createElement("div");
      aviso.className = "list-group-item text-danger";
      aviso.textContent = error.message;
      contenedor.appendChild(aviso);
    }
  }
}

const campoUbicacionMerma = document.getElementById("ubicacion_merma");
const contenedorUbicacionMerma = campoUbicacionMerma.nextElementSibling;
const botonUbicacionMerma = contenedorUbicacionMerma.querySelector("button");
const opcionesUbicacionMerma = contenedorUbicacionMerma.querySelector(".options");
const busquedaUbicacionMerma = contenedorUbicacionMerma.querySelector(".search-box input");

botonUbicacionMerma.addEventListener("click", async () => {
  const menu = contenedorUbicacionMerma.querySelector(".dropdown-menu");
  menu.classList.toggle("show");
  if (menu.classList.contains("show")) {
    busquedaUbicacionMerma.focus();
    await buscarUbicaciones(busquedaUbicacionMerma.value.trim(), opcionesUbicacionMerma);
  }
});

opcionesUbicacionMerma.addEventListener("click", async (event) => {
  const opcion = event.target.closest("button[data-value]");
  if (!opcion) return;
  const ubicacionCambio = String(opcion.dataset.value) !== ubicacionMermaActual;
  campoUbicacionMerma.value = opcion.dataset.value;
  ubicacionMermaActual = opcion.dataset.value;
  botonUbicacionMerma.textContent = opcion.dataset.label;
  contenedorUbicacionMerma.querySelector(".dropdown-menu").classList.remove("show");

  if (ubicacionCambio) {
    solicitudInventarioMerma?.abort();
    inventarioMermaSeleccionado = {};
    document.getElementById("tablaMerma").replaceChildren();
    reordenarTablaMerma();
    await cargarInventarioMerma(1, "");
  }
});

busquedaUbicacionMerma.addEventListener("input", () => {
  clearTimeout(busquedaUbicacionMerma.timer);
  busquedaUbicacionMerma.timer = setTimeout(
    () => buscarUbicaciones(busquedaUbicacionMerma.value.trim(), opcionesUbicacionMerma),
    250,
  );
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".select-container")) {
    contenedorUbicacionMerma.querySelector(".dropdown-menu").classList.remove("show");
  }
});

async function cargarInventarioMerma(pagina = 1, busqueda = "") {
  const lista = document.getElementById("contenedorProductosAjax");
  if (!ubicacionMermaActual) {
    lista.textContent = "Seleccione una sucursal para consultar su inventario.";
    return;
  }
  lista.innerHTML = `
    <div class="text-center py-4" role="status">
      <span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
      Cargando inventario...
    </div>`;
  paginaInventarioMerma = pagina;
  busquedaInventarioMerma = busqueda;
  const params = new URLSearchParams({ page: pagina, limit: 20 });
  if (busqueda) params.set("search", busqueda);
  const claveCache = `${ubicacionMermaActual}:${pagina}:${busqueda}`;
  const cacheGuardado = cacheInventarioMerma.get(claveCache);
  let data = cacheGuardado && Date.now() - cacheGuardado.fecha < 15000
    ? cacheGuardado.data
    : null;
  if (!data && cacheGuardado) cacheInventarioMerma.delete(claveCache);
  solicitudInventarioMerma?.abort();
  solicitudInventarioMerma = new AbortController();
  const solicitud = solicitudInventarioMerma;
  try {
    if (!data) {
      const response = await fetch(
        `/manager/inventario/merma/ubicacion/${ubicacionMermaActual}/?${params}`,
        { signal: solicitud.signal },
      );
      data = await response.json();
      if (!response.ok) throw new Error(data.error || "No se pudo cargar el inventario.");
      if (solicitud !== solicitudInventarioMerma) return;
      cacheInventarioMerma.set(claveCache, { data, fecha: Date.now() });
      if (cacheInventarioMerma.size > 20) {
        cacheInventarioMerma.delete(cacheInventarioMerma.keys().next().value);
      }
    }
    if (
      solicitud !== solicitudInventarioMerma ||
      claveCache !== `${ubicacionMermaActual}:${paginaInventarioMerma}:${busquedaInventarioMerma}`
    ) return;
    lista.replaceChildren();
    if (!data.results.length) {
      lista.textContent = "No hay productos disponibles en esta sucursal.";
      renderPaginacionMerma(data.page, data.totalPages);
      return;
    }
    data.results.forEach((producto) => {
      const opcion = document.createElement("div");
      opcion.className = "productosstyle producto-item compras-product-option";
      opcion.innerHTML = `
        <img class="compras-product-option__image" src="${escaparHtml(producto.imagen || "/static/img/default.webp")}" alt="">
        <div class="compras-product-option__info datos-producto"
             data-sku="${escaparHtml(producto.sku)}"
             data-stock="${escaparHtml(producto.stock)}">
          <strong>${escaparHtml(producto.nombre)}</strong>
          <small>SKU: ${escaparHtml(producto.sku)} · Existencias: ${formatoStockMerma(producto.stock)}</small>
        </div>
        <span class="compras-product-option__action"></span>
        <input type="checkbox" class="form-check-input producto-checkbox d-none" value="${producto.producto_id}">`;
      opcion.querySelector("img").addEventListener("error", (event) => {
        event.currentTarget.src = "/static/img/default.webp";
      });
      lista.appendChild(opcion);
    });
    inicializarSeleccionMerma();
    renderPaginacionMerma(data.page, data.totalPages);
  } catch (error) {
    if (error.name !== "AbortError" && solicitud === solicitudInventarioMerma) {
      lista.textContent = error.message;
    }
  }
}

function renderPaginacionMerma(pagina, totalPaginas) {
  const paginador = document.getElementById("paginacionProductos");
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
    boton.addEventListener("click", () =>
      cargarInventarioMerma(destino, busquedaInventarioMerma),
    );
    item.appendChild(boton);
    paginador.appendChild(item);
  };
  crearBoton("«", pagina - 1, pagina === 1);
  for (let numero = Math.max(1, pagina - 2); numero <= Math.min(totalPaginas, pagina + 2); numero += 1) {
    crearBoton(String(numero), numero, false, numero === pagina);
  }
  crearBoton("»", pagina + 1, pagina === totalPaginas);
}

function inicializarSeleccionMerma() {
  document.querySelectorAll("#contenedorProductosAjax .producto-item").forEach((opcion) => {
    const checkbox = opcion.querySelector(".producto-checkbox");
    const id = checkbox.value;
    const actualizarEtiqueta = () => {
      const etiqueta = opcion.querySelector(".compras-product-option__action");
      etiqueta.innerHTML = checkbox.checked
        ? '<i class="bx bx-check-circle"></i> Seleccionado'
        : '<i class="bx bx-plus-circle"></i> Seleccionar';
    };
    if (inventarioMermaSeleccionado[id]) {
      checkbox.checked = true;
      opcion.classList.add("seleccionado");
    }
    actualizarEtiqueta();
    opcion.addEventListener("click", () => {
      checkbox.checked = !checkbox.checked;
      opcion.classList.toggle("seleccionado", checkbox.checked);
      actualizarEtiqueta();
      if (checkbox.checked) {
        const datos = opcion.querySelector(".datos-producto");
        inventarioMermaSeleccionado[id] = {
          producto_id: Number(id),
          nombre: opcion.querySelector("strong").textContent,
          sku: datos.dataset.sku,
          stock: datos.dataset.stock,
        };
      } else {
        delete inventarioMermaSeleccionado[id];
      }
    });
  });
}

function renderizarTarjetasMerma() {
  const tbody = document.getElementById("tablaMerma");
  const contenedor = tbody.closest(".traslado-editor-mobile");
  const lista = contenedor.querySelector(".traslados-editor-mobile-list");
  lista.replaceChildren();
  if (!window.matchMedia("(max-width: 1032px)").matches) return;
  [...tbody.querySelectorAll("tr")].forEach((fila, index) => {
    const celdas = fila.children;
    const cantidad = fila.querySelector(".cantidad-final");
    const eliminar = fila.querySelector(".eliminar-merma");
    const tarjeta = document.createElement("article");
    tarjeta.className = "traslados-editor-mobile-card";
    tarjeta.innerHTML = `
      <header><span class="traslados-editor-mobile-card__icon"><i class="bx bx-trash"></i></span>
        <div><small>Producto ${index + 1}</small><strong>${escaparHtml(celdas[1].textContent)}</strong></div></header>
      <div class="traslados-editor-mobile-card__meta">
        <div><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escaparHtml(celdas[2].textContent)}</strong></span></div>
        <div><i class="bx bx-box"></i><span><small>Stock disponible</small><strong>${escaparHtml(celdas[3].textContent)}</strong></span></div>
      </div><div class="traslados-editor-mobile-card__controls"></div><footer></footer>`;
    const campo = document.createElement("label");
    campo.innerHTML = "<small>Cantidad a retirar</small>";
    const espejo = cantidad.cloneNode(true);
    espejo.removeAttribute("id");
    espejo.addEventListener("input", () => {
      cantidad.value = espejo.value;
      cantidad.dispatchEvent(new Event("input", { bubbles: true }));
    });
    cantidad.oninput = () => {
      espejo.value = cantidad.value;
    };
    campo.appendChild(espejo);
    tarjeta.querySelector(".traslados-editor-mobile-card__controls").appendChild(campo);
    const botonEliminar = document.createElement("button");
    botonEliminar.type = "button";
    botonEliminar.className = "btn btn-danger";
    botonEliminar.innerHTML = '<i class="bx bx-trash"></i><span>Eliminar</span>';
    botonEliminar.addEventListener("click", () => eliminar.click());
    tarjeta.querySelector("footer").appendChild(botonEliminar);
    lista.appendChild(tarjeta);
  });
}

function renderizarPreviewMermaMovil() {
  const tbody = document.getElementById("tablaPreviewMerma");
  const lista = tbody.closest(".traslado-mobile-modal").querySelector(".traslados-confirmar-mobile-list");
  lista.replaceChildren();
  [...tbody.querySelectorAll("tr")].forEach((fila, index) => {
    const celdas = fila.children;
    const nombre = celdas[1].textContent;
    const sku = celdas[2].textContent;
    const stock = celdas[3].textContent;
    const cantidad = celdas[4].textContent;
    const tarjeta = document.createElement("article");
    tarjeta.className = "traslados-confirmar-mobile-card";
    tarjeta.innerHTML = `
      <header><span class="traslados-confirmar-mobile-card__icon"><i class="bx bx-trash"></i></span>
        <div><small>Producto ${index + 1}</small><strong>${escaparHtml(nombre)}</strong></div>
        <span class="traslados-confirmar-mobile-card__quantity">${escaparHtml(cantidad)}</span></header>
      <div class="traslados-confirmar-mobile-card__meta">
        <div><i class="bx bx-barcode"></i><span><small>SKU</small><strong>${escaparHtml(sku)}</strong></span></div>
        <div><i class="bx bx-box"></i><span><small>Stock disponible</small><strong>${escaparHtml(stock)}</strong></span></div>
      </div><div class="traslados-confirmar-mobile-card__amount"><small>Cantidad a retirar</small><strong>${escaparHtml(cantidad)}</strong></div>`;
    lista.appendChild(tarjeta);
  });
}

new MutationObserver(renderizarTarjetasMerma).observe(
  document.getElementById("tablaMerma"),
  { childList: true, subtree: true },
);
window.addEventListener("resize", renderizarTarjetasMerma);

document.getElementById("toggleDropdownPanel").addEventListener("click", () => {
  if (!ubicacionMermaActual) {
    Swal.fire({
      title: "Sucursal requerida",
      text: "Selecciona una sucursal antes de agregar productos.",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalregis")).show();
  cargarInventarioMerma(paginaInventarioMerma, busquedaInventarioMerma);
});

document.getElementById("formBuscarProductosCompra").addEventListener("submit", (event) => {
  event.preventDefault();
  const buscador = document.getElementById("buscadorProductos");
  clearTimeout(buscador.searchTimer);
  const busqueda = buscador.value.trim();
  cargarInventarioMerma(1, busqueda);
});

document.getElementById("buscadorProductos").addEventListener("input", (event) => {
  const buscador = event.currentTarget;
  clearTimeout(buscador.searchTimer);
  buscador.searchTimer = setTimeout(() => {
    cargarInventarioMerma(1, buscador.value.trim());
  }, 300);
});

document.getElementById("guardarProductosSeleccionados").addEventListener("click", () => {
  const tabla = document.getElementById("tablaMerma");
  Object.entries(inventarioMermaSeleccionado).forEach(([id, producto]) => {
    if (document.getElementById(`merma-${id}`)) return;
    const stock = Number(producto.stock);
    const inicial = Math.min(1, stock);
    const fila = document.createElement("tr");
    fila.id = `merma-${id}`;
    fila.dataset.stock = String(stock);
    fila.innerHTML = `
      <td></td>
      <td>${escaparHtml(producto.nombre)}</td>
      <td>${escaparHtml(producto.sku)}</td>
      <td>${formatoStockMerma(stock)}</td>
      <td><input type="number" class="form-control cantidad-final" min="0.000001" max="${stock}" step="0.000001" value="${inicial}" aria-label="Cantidad a retirar de ${escaparHtml(producto.nombre)}"></td>
      <td><button type="button" class="btn btn-danger btn-sm eliminar-merma" aria-label="Quitar producto"><i class="bx bx-trash"></i></button></td>`;
    tabla.appendChild(fila);
  });
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalregis")).hide();
  reordenarTablaMerma();
});

document.getElementById("tablaMerma").addEventListener("click", (event) => {
  const boton = event.target.closest(".eliminar-merma");
  if (!boton) return;
  const fila = boton.closest("tr");
  delete inventarioMermaSeleccionado[fila.id.replace("merma-", "")];
  fila.remove();
  reordenarTablaMerma();
});

function reordenarTablaMerma() {
  document.querySelectorAll("#tablaMerma tr").forEach((fila, index) => {
    fila.children[0].textContent = String(index + 1);
  });
}

document.getElementById("btnPreviewMerma").addEventListener("click", () => {
  const filas = [...document.querySelectorAll("#tablaMerma tr")];
  if (!ubicacionMermaActual || !filas.length) {
    Swal.fire({
      title: "Datos incompletos",
      text: "Selecciona una sucursal y agrega al menos un producto.",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }
  document.getElementById("previewUbicacionMerma").value = botonUbicacionMerma.textContent;
  const preview = document.getElementById("tablaPreviewMerma");
  preview.replaceChildren();
  filas.forEach((fila, index) => {
    const resumen = document.createElement("tr");
    resumen.innerHTML = `
      <td>${index + 1}</td>
      <td>${escaparHtml(fila.children[1].textContent)}</td>
      <td>${escaparHtml(fila.children[2].textContent)}</td>
      <td>${escaparHtml(fila.children[3].textContent)}</td>
      <td>${escaparHtml(fila.querySelector(".cantidad-final").value)}</td>`;
    preview.appendChild(resumen);
  });
  renderizarPreviewMermaMovil();
  bootstrap.Modal.getOrCreateInstance(document.getElementById("confirmarMerma")).show();
});

document.getElementById("confirmarMermaBtn").addEventListener("click", async (event) => {
  const botonConfirmar = event.currentTarget;
  const motivo = document.getElementById("motivoMerma").value;
  const filas = [...document.querySelectorAll("#tablaMerma tr")];
  if (!motivo) {
    document.getElementById("motivoMerma").focus();
    Swal.fire({
      title: "Motivo requerido",
      text: "Selecciona el motivo del retiro para continuar.",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }
  const detalles = filas.map((fila) => ({
    productoId: Number(fila.id.replace("merma-", "")),
    cantidad: fila.querySelector(".cantidad-final").value,
  }));
  const cantidadesValidas = filas.every((fila) => {
    const cantidad = Number(fila.querySelector(".cantidad-final").value);
    return Number.isFinite(cantidad) && cantidad > 0 && cantidad <= Number(fila.dataset.stock);
  });
  if (!cantidadesValidas) {
    Swal.fire({
      title: "Cantidad inválida",
      text: "Indica una cantidad mayor que cero y no superior al stock disponible.",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }

  botonConfirmar.disabled = true;
  try {
    const response = await fetch("/manager/merma/post/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
      },
      body: JSON.stringify({
        ubicacionId: Number(ubicacionMermaActual),
        motivo,
        observaciones: document.getElementById("observacionesMerma").value.trim(),
        detalles,
      }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.message || "No se pudo registrar la merma.");
    bootstrap.Modal.getOrCreateInstance(document.getElementById("confirmarMerma")).hide();
    Swal.fire({
      title: "Merma registrada",
      text: data.message,
      icon: "success",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    }).then(() => {
      window.location.assign(botonConfirmar.dataset.listUrl);
    });
  } catch (error) {
    Swal.fire({
      title: "No se pudo registrar",
      text: error.message,
      icon: "error",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
  } finally {
    botonConfirmar.disabled = false;
  }
});
