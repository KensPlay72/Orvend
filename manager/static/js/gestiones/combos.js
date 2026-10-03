function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, "");
}

document.addEventListener("DOMContentLoaded", () => {
  const productos = JSON.parse(
    document.getElementById("combos-productos").textContent,
  );
  const seleccionados = new Map();
  const pendientes = new Set();
  const porPagina = 10;
  let paginaActual = 1;
  let terminoBusqueda = "";
  const detalle = document.getElementById("detalleCombo");
  const lista = document.getElementById("listaProductosCombo");
  const paginador = document.getElementById("paginadorProductosCombo");
  const buscador = document.getElementById("buscarProductoCombo");
  const textoSeleccionados = document.getElementById(
    "productosSeleccionadosTexto",
  );
  const costoTotal = document.getElementById("costoTotal");
  const utilidadTotal = document.getElementById("utilidadTotal");
  const modalProductos = document.getElementById("modalProductosCombo");
  const inputImagenCombo = document.getElementById("comboImagen");
  const imagenComboPreview = document.getElementById("comboImagenPreview");
  let imagenCombo = null;
  const formato = (valor) =>
    `${window.MONEDA_SISTEMA || "L."} ${Number(valor || 0).toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const escapar = (valor) =>
    String(valor ?? "").replace(
      /[&<>'"]/g,
      (caracter) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "'": "&#039;",
          '"': "&quot;",
        })[caracter],
    );

  function calcular() {
    const costo = [...seleccionados.values()].reduce(
      (total, item) => total + item.costo * item.cantidad,
      0,
    );
    const venta = Number(document.getElementById("precioVenta").value || 0);
    costoTotal.textContent = formato(costo);
    utilidadTotal.textContent = formato(venta - costo);
  }

  function renderDetalle() {
    if (!seleccionados.size) {
      detalle.innerHTML =
        '<tr class="combos-empty"><td colspan="6"><i class="bx bx-package"></i><span>Aún no has agregado productos al combo.</span></td></tr>';
      calcular();
      return;
    }
    detalle.innerHTML = [...seleccionados.values()]
      .map(
        (item) =>
          `<tr data-id="${item.id}"><td><div class="combos-product-name"><strong>${escapar(item.nombre)}</strong><span>${escapar(item.sku)} · ${escapar(item.presentacion)}</span></div></td><td class="combos-stock">${item.stock}</td><td><input class="combos-qty" type="text" inputmode="numeric" oninput="validateNumber(this)" value="${item.cantidad}" aria-label="Cantidad de ${escapar(item.nombre)}"></td><td>${formato(item.costo)}</td><td class="combos-subtotal">${formato(item.costo * item.cantidad)}</td><td><button type="button" class="combos-remove" aria-label="Quitar ${escapar(item.nombre)}"><i class="bx bx-trash"></i></button></td></tr>`,
      )
      .join("");
    calcular();
  }

  function renderPaginador(totalPaginas) {
    const inicioPagina = Math.max(1, paginaActual - 2);
    const finPagina = Math.min(totalPaginas, paginaActual + 2);
    const paginas = Array.from(
      { length: finPagina - inicioPagina + 1 },
      (_, indice) =>
        `<button type="button" class="${paginaActual === inicioPagina + indice ? "is-current" : ""}" data-page="${inicioPagina + indice}">${inicioPagina + indice}</button>`,
    ).join("");
    paginador.innerHTML = `<button type="button" data-page="${paginaActual - 1}" ${paginaActual === 1 ? "disabled" : ""} aria-label="Página anterior"><i class="bx bx-chevron-left"></i></button>${paginas}<button type="button" data-page="${paginaActual + 1}" ${paginaActual === totalPaginas ? "disabled" : ""} aria-label="Página siguiente"><i class="bx bx-chevron-right"></i></button>`;
  }

  function renderProductos() {
    const termino = terminoBusqueda.toLowerCase();
    const filtrados = productos.filter(
      (producto) =>
        !termino ||
        `${producto.nombre} ${producto.sku}`.toLowerCase().includes(termino),
    );
    const totalPaginas = Math.max(1, Math.ceil(filtrados.length / porPagina));
    paginaActual = Math.min(paginaActual, totalPaginas);
    const visibles = filtrados.slice(
      (paginaActual - 1) * porPagina,
      paginaActual * porPagina,
    );
    lista.innerHTML = visibles.length
      ? visibles
          .map((producto) => {
            const agregado = seleccionados.has(producto.id);
            const pendiente = pendientes.has(producto.id);
            const estado = agregado
              ? '<i class="bx bx-check-circle"></i> Agregado'
              : pendiente
                ? '<i class="bx bx-check-circle"></i> Seleccionado'
                : '<i class="bx bx-plus-circle"></i> Seleccionar';
            return `<button type="button" class="combos-product-option ${agregado || pendiente ? "is-selected" : ""}" data-id="${producto.id}" aria-pressed="${agregado || pendiente}"><img src="${escapar(producto.imagen)}" alt="" class="combos-product-image" onerror="this.src='/static/img/default.png'"><span class="combos-product-option__info"><strong>${escapar(producto.nombre)}</strong><span>Existencias en inventario: <b>${producto.stock}</b></span></span><b class="combos-product-option__state">${estado}</b></button>`;
          })
          .join("")
      : '<p class="text-center text-muted py-4">No se encontraron productos disponibles.</p>';
    renderPaginador(totalPaginas);
    textoSeleccionados.textContent = `${pendientes.size} producto${pendientes.size === 1 ? "" : "s"} seleccionado${pendientes.size === 1 ? "" : "s"}`;
  }

  document.getElementById("abrirProductos").addEventListener("click", () => {
    terminoBusqueda = "";
    paginaActual = 1;
    buscador.value = "";
    renderProductos();
  });
  document
    .getElementById("formBuscarProductoCombo")
    .addEventListener("submit", (evento) => {
      evento.preventDefault();
      terminoBusqueda = buscador.value.trim();
      paginaActual = 1;
      renderProductos();
    });
  paginador.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-page]");
    if (boton && !boton.disabled) {
      paginaActual = Number(boton.dataset.page);
      renderProductos();
    }
  });
  lista.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-id]");
    if (!boton) return;
    const id = Number(boton.dataset.id);
    if (seleccionados.has(id)) return;
    if (pendientes.has(id)) pendientes.delete(id);
    else pendientes.add(id);
    renderProductos();
  });
  document
    .getElementById("agregarSeleccionados")
    .addEventListener("click", () => {
      pendientes.forEach((id) => {
        const producto = productos.find((item) => item.id === id);
        if (producto && !seleccionados.has(id))
          seleccionados.set(id, { ...producto, cantidad: 1 });
      });
      pendientes.clear();
      renderDetalle();
      renderProductos();
      bootstrap.Modal.getInstance(modalProductos)?.hide();
    });
  detalle.addEventListener("input", (evento) => {
    if (!evento.target.classList.contains("combos-qty")) return;
    const item = seleccionados.get(
      Number(evento.target.closest("tr").dataset.id),
    );
    item.cantidad = Math.min(
      item.stock,
      Math.max(1, Number(evento.target.value || 1)),
    );
    renderDetalle();
  });
  detalle.addEventListener("click", (evento) => {
    const boton = evento.target.closest(".combos-remove");
    if (boton) {
      seleccionados.delete(Number(boton.closest("tr").dataset.id));
      renderDetalle();
    }
  });
  document.getElementById("precioVenta").addEventListener("input", calcular);

  inputImagenCombo.addEventListener("change", () => {
    const archivo = inputImagenCombo.files?.[0];
    if (!archivo) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(archivo.type)) {
      inputImagenCombo.value = "";
      imagenCombo = null;
      imagenComboPreview.src = "/static/img/default.png";
      Swal.fire({
        icon: "warning",
        title: "Formato inválido",
        text: "Selecciona una imagen JPG, PNG o WEBP.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    imagenCombo = archivo;
    imagenComboPreview.src = URL.createObjectURL(archivo);
  });

  imagenComboPreview.addEventListener("error", () => {
    imagenComboPreview.src = "/static/img/default.png";
  });

  const obtenerCsrf = () =>
    document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  const guardarCombo = document.getElementById("guardarCombo");
  guardarCombo?.addEventListener("click", async () => {
    const nombre = document.getElementById("comboNombre").value.trim();
    const codigoSku = document.getElementById("comboSku").value.trim();
    const precioVenta = document.getElementById("precioVenta").value;
    const precioMinimo = document.getElementById("precioMinimo").value;
    const precioMaximo = document.getElementById("precioMaximo").value;
    if (
      !nombre ||
      !codigoSku ||
      !precioVenta ||
      !precioMinimo ||
      !precioMaximo ||
      !seleccionados.size
    ) {
      Swal.fire({
        icon: "warning",
        title: "Datos incompletos",
        text: "Completa los datos, precios y agrega al menos un producto.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    try {
      guardarCombo.disabled = true;
      const formulario = new FormData();
      formulario.append("nombre", nombre);
      formulario.append("codigo_sku", codigoSku);
      formulario.append("precio_venta", precioVenta);
      formulario.append("precio_minimo", precioMinimo);
      formulario.append("precio_maximo", precioMaximo);
      formulario.append(
        "detalles",
        JSON.stringify(
          [...seleccionados.values()].map((item) => ({
            producto_id: item.id,
            cantidad: item.cantidad,
          })),
        ),
      );
      if (imagenCombo) formulario.append("imagen", imagenCombo);

      const respuesta = await fetch(COMBOS_URLS.guardar, {
        method: "POST",
        headers: { "X-CSRFToken": obtenerCsrf() },
        body: formulario,
      });
      const contenido = await respuesta.text();
      let datos = {};
      try {
        datos = JSON.parse(contenido);
      } catch (_) {
        throw new Error("El servidor no pudo procesar el registro del combo.");
      }
      if (!respuesta.ok || !datos.success) {
        throw new Error(datos.message || "No fue posible registrar el combo.");
      }
      await Swal.fire({
        icon: "success",
        title: "Combo registrado",
        text: datos.message,
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      window.location.reload();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "No se pudo registrar",
        text: error.message || "Inténtalo nuevamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      guardarCombo.disabled = false;
    }
  });
});
