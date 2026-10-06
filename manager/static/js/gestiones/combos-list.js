document.addEventListener("DOMContentLoaded", () => {
  const tabla = document.getElementById("listaCombosRegistrados");
  const listaMovil = document.getElementById("combosMobileList");
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const detalleProductos = document.getElementById("detalleProductosCombo");
  const tituloDetalle = document.getElementById("modalDetalleComboTitulo");
  const skuDetalle = document.getElementById("detalleComboSku");
  const modalDetalle = document.getElementById("modalDetalleCombo");
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

  async function cargarDetalle(comboId, destino, actualizarTitulo = false) {
    destino.innerHTML = '<p class="text-center text-muted py-4">Cargando productos…</p>';
    try {
      const respuesta = await fetch(
        COMBO_LIST_URLS.detalle.replace("/0/", `/${comboId}/`),
      );
      if (!respuesta.ok)
        throw new Error("No fue posible obtener los productos del combo.");
      const datos = await respuesta.json();
      if (!datos.success)
        throw new Error("No fue posible obtener los productos del combo.");
      if (actualizarTitulo) {
        tituloDetalle.textContent = datos.combo.nombre;
        skuDetalle.textContent = `SKU: ${datos.combo.sku}`;
      }
      destino.innerHTML = datos.detalles.length
        ? datos.detalles
            .map(
              (producto) =>
                `<div class="combos-product-option combos-detail-product"><img src="${escapar(producto.imagen)}" alt="" class="combos-product-image" onerror="this.src='/static/img/default.png'"><span class="combos-product-option__info"><strong>${escapar(producto.nombre)}</strong><span>${escapar(producto.presentacion)} · SKU: ${escapar(producto.sku)}</span></span><b class="combos-product-option__state">Cantidad: ${escapar(producto.cantidad)}</b></div>`,
            )
            .join("")
        : '<p class="text-center text-muted py-4">Este combo no tiene productos.</p>';
    } catch (error) {
      destino.innerHTML = `<p class="text-center text-danger py-4">${escapar(error.message)}</p>`;
    }
  }

  async function mostrarDetalle(comboId) {
    tituloDetalle.textContent = "Productos del combo";
    skuDetalle.textContent = "";
    bootstrap.Modal.getOrCreateInstance(modalDetalle).show();
    await cargarDetalle(comboId, detalleProductos, true);
  }

  async function cambiarEstado(boton) {
    const activo = boton.dataset.activo === "true";
    const resultado = await Swal.fire({
      icon: "warning",
      title: `¿${activo ? "Inactivar" : "Activar"} este combo?`,
      text: activo
        ? "El combo dejará de estar disponible para su venta."
        : "El combo volverá a estar disponible para su venta.",
      showCancelButton: true,
      confirmButtonText: "Aceptar",
      cancelButtonText: "Cancelar",
      customClass: { confirmButton: "classbotones" },
    });
    if (!resultado.isConfirmed) return;
    try {
      const respuesta = await fetch(
        COMBO_LIST_URLS.estado.replace("/0/", `/${boton.dataset.comboId}/`),
        { method: "POST", headers: { "X-CSRFToken": csrf } },
      );
      const datos = await respuesta.json();
      if (!respuesta.ok || !datos.success) throw new Error(datos.message);
      await Swal.fire({
        icon: "success",
        title: "Proceso completado",
        text: datos.message,
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      window.location.reload();
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "No se pudo actualizar",
        text: error.message || "Inténtalo nuevamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  }

  tabla?.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-activo]");
    if (boton) {
      evento.stopPropagation();
      cambiarEstado(boton);
      return;
    }
    const fila = evento.target.closest(".combos-list-row");
    if (fila) mostrarDetalle(fila.dataset.comboId);
  });

  listaMovil?.addEventListener("click", (evento) => {
    const botonEstado = evento.target.closest("[data-activo]");
    if (botonEstado) {
      evento.stopPropagation();
      cambiarEstado(botonEstado);
      return;
    }
    const encabezado = evento.target.closest(".combos-mobile-card__header");
    if (!encabezado) return;
    const tarjeta = encabezado.closest(".combos-mobile-card");
    const abierta = tarjeta.classList.toggle("is-open");
    encabezado.setAttribute("aria-expanded", String(abierta));
    if (abierta) {
      const destino = tarjeta.querySelector(".combos-mobile-card__products");
      if (!destino.dataset.cargado) {
        destino.dataset.cargado = "true";
        cargarDetalle(tarjeta.dataset.comboId, destino);
      }
    }
  });
});
