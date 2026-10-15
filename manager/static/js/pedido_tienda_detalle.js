document.addEventListener("DOMContentLoaded", async () => {
  // ========================================================
  // CONFIGURACIÓN LEÍDA DE LOS DATA ATTRIBUTES DEL DOM
  // ========================================================
  const rootEl =
    document.getElementById("pedidoManagerDetalle") ||
    document.querySelector(".pedido-manager-detalle");

  if (!rootEl) return;

  const urlBuscarProductos =
    rootEl.dataset.urlBuscar || "/manager/pedidos-tienda/buscar-productos/";
  const sucursalId = rootEl.dataset.sucursalId || "";
  const puedeModificarPrecio = rootEl.dataset.puedeModificarPrecio === "true";
  const urlCambiarBase = rootEl.dataset.urlCambiar || "";
  const urlAnexarBase = rootEl.dataset.urlAnexar || "";
  const monedaSimbolo = rootEl.dataset.monedaSimbolo || "L.";

  // ========================================================
  // ELEMENTOS MODALES DE SELECCIÓN Y CONFIGURACIÓN
  // ========================================================
  const modalSelectorEl = document.getElementById("modalSelectorProductosPedido");
  const modalConfigEl = document.getElementById("modalConfigurarProductoPedido");
  const modalSelector =
    modalSelectorEl && typeof bootstrap !== "undefined"
      ? bootstrap.Modal.getOrCreateInstance(modalSelectorEl)
      : null;
  const modalConfig =
    modalConfigEl && typeof bootstrap !== "undefined"
      ? bootstrap.Modal.getOrCreateInstance(modalConfigEl)
      : null;

  let estadoSelector = {
    modo: null, // 'anexar' | 'cambiar'
    detalleId: null,
    nombreOriginal: "",
    cantidadOriginal: "",
    productoSeleccionado: null,
    pagina: 1,
    busqueda: "",
  };

  const listaProductosPedido = document.getElementById("listaProductosPedido");
  const paginacionProductosPedido = document.getElementById("paginacionProductosPedido");
  const inputBuscarProductosPedido = document.getElementById("inputBuscarProductosPedido");
  const formBuscarProductosPedido = document.getElementById("formBuscarProductosPedido");

  // Elementos del Modal de Configuración
  const formConfirmarProductoPedido = document.getElementById("formConfirmarProductoPedido");
  const tituloConfigurarProducto = document.getElementById("tituloConfigurarProducto");
  const bloqueProductoOriginalCambio = document.getElementById("bloqueProductoOriginalCambio");
  const boxProductoOriginalCambio = document.getElementById("boxProductoOriginalCambio");
  const boxProductoNuevoSustituto = document.getElementById("boxProductoNuevoSustituto");
  const boxProductoSeleccionado = document.getElementById("boxProductoSeleccionado");
  const nombreProductoOriginalCambio = document.getElementById("nombreProductoOriginalCambio");
  const imgProductoOriginalCambio = document.getElementById("imgProductoOriginalCambio");
  const cantProductoOriginalCambio = document.getElementById("cantProductoOriginalCambio");
  const configProductoImg = document.getElementById("configProductoImg");
  const configProductoNombre = document.getElementById("configProductoNombre");
  const configProductoSku = document.getElementById("configProductoSku");
  const configProductoStock = document.getElementById("configProductoStock");
  const configProductoUnidad = document.getElementById("configProductoUnidad");
  const modalInputPrecio = document.getElementById("modalInputPrecio");
  const modalHiddenPrecio = document.getElementById("modalHiddenPrecio");
  const helperPrecioLimites = document.getElementById("helperPrecioLimites");
  const modalInputCantidad = document.getElementById("modalInputCantidad");
  const btnQtyDisminuir = document.getElementById("btnQtyDisminuir");
  const btnQtyAumentar = document.getElementById("btnQtyAumentar");
  const modalSubtotalEstimado = document.getElementById("modalSubtotalEstimado");
  const divJustificacionCambio = document.getElementById("divJustificacionCambio");
  const modalInputJustificacion = document.getElementById("modalInputJustificacion");
  const btnVolverAlSelector = document.getElementById("btnVolverAlSelector");
  const btnConfirmarProducto = document.getElementById("btnConfirmarProducto");
  const configDetalleId = document.getElementById("configDetalleId");
  const configProductoIdCambio = document.getElementById("configProductoIdCambio");
  const configProductoIdAnexo = document.getElementById("configProductoIdAnexo");

  // Calcular subtotal estimado
  function actualizarSubtotalEstimado() {
    if (!modalSubtotalEstimado) return;
    const cant = parseFloat(modalInputCantidad?.value) || 0;
    let precio = 0;
    if (puedeModificarPrecio) {
      precio = parseFloat(modalInputPrecio?.value) || 0;
    } else {
      precio = parseFloat(modalHiddenPrecio?.value || modalInputPrecio?.value) || 0;
    }
    const subtotal = Math.max(0, cant * precio);
    modalSubtotalEstimado.textContent = subtotal.toFixed(2);
  }

  // Cargar catálogo de productos por Ajax con paginación
  async function cargarCatalogo(pagina = 1) {
    if (!listaProductosPedido) return;
    listaProductosPedido.classList.add("is-loading");
    listaProductosPedido.innerHTML =
      '<div class="text-center py-4 text-muted"><i class="bx bx-loader-alt bx-spin fs-4"></i><div class="mt-1 small">Cargando productos...</div></div>';

    try {
      const url = new URL(urlBuscarProductos, window.location.origin);
      url.searchParams.set("sucursal", sucursalId);
      url.searchParams.set("page", pagina);
      url.searchParams.set("limit", 10);
      if (estadoSelector.busqueda) {
        url.searchParams.set("q", estadoSelector.busqueda);
      }

      const resp = await fetch(url.toString());
      const data = await resp.json();

      if (!data.success || !data.productos || data.productos.length === 0) {
        listaProductosPedido.innerHTML =
          '<div class="text-center py-4 text-muted small"><i class="bx bx-search-alt fs-2 d-block mb-1"></i>No se encontraron productos disponibles con stock en esta sucursal.</div>';
        if (paginacionProductosPedido) paginacionProductosPedido.innerHTML = "";
        listaProductosPedido.classList.remove("is-loading");
        return;
      }

      estadoSelector.pagina = data.current_page || pagina;

      listaProductosPedido.innerHTML = data.productos
        .map((prod) => {
          const dataProd = encodeURIComponent(JSON.stringify(prod));
          return `
            <div class="caja-product-option" data-producto="${dataProd}">
              <img
                class="caja-product-option__image"
                src="${prod.imagen_url}"
                alt="${prod.nombre}"
                onerror="this.onerror=null; this.src='/static/img/default.webp';"
              />
              <div class="caja-product-option__info">
                <strong>${prod.nombre}</strong>
                <small>SKU: ${prod.codigo_sku || "N/A"} · Stock: <b class="text-success">${prod.stock_disponible}</b> ${prod.unidad || "ud"}</small>
              </div>
              <div class="caja-product-option__action">
                <span class="caja-product-option__price">${monedaSimbolo} ${prod.precio.toFixed(2)}</span>
                <span class="caja-product-option__btn"><i class="bx bx-plus-circle"></i> Seleccionar</span>
              </div>
            </div>
          `;
        })
        .join("");

      // Controles de Paginación
      if (paginacionProductosPedido) {
        const totalPages = data.total_pages || 1;
        const curr = data.current_page || 1;
        if (totalPages <= 1) {
          paginacionProductosPedido.innerHTML = "";
        } else {
          let htmlPag = `
            <li class="page-item ${curr <= 1 ? "disabled" : ""}">
              <button type="button" class="page-link" data-page="${curr - 1}">«</button>
            </li>
          `;
          const startP = Math.max(1, curr - 2);
          const endP = Math.min(totalPages, curr + 2);
          for (let i = startP; i <= endP; i++) {
            htmlPag += `
              <li class="page-item ${i === curr ? "active" : ""}">
                <button type="button" class="page-link" data-page="${i}">${i}</button>
              </li>
            `;
          }
          htmlPag += `
            <li class="page-item ${curr >= totalPages ? "disabled" : ""}">
              <button type="button" class="page-link" data-page="${curr + 1}">»</button>
            </li>
          `;
          paginacionProductosPedido.innerHTML = htmlPag;

          paginacionProductosPedido.querySelectorAll("[data-page]").forEach((btn) => {
            btn.onclick = () => {
              if (!btn.closest(".page-item")?.classList.contains("disabled")) {
                cargarCatalogo(parseInt(btn.dataset.page));
              }
            };
          });
        }
      }

      // Evento clic en tarjeta de producto
      listaProductosPedido.querySelectorAll(".caja-product-option").forEach((card) => {
        card.onclick = () => {
          const raw = decodeURIComponent(card.dataset.producto);
          try {
            const producto = JSON.parse(raw);
            seleccionarProductoYConfigurar(producto);
          } catch (err) {
            console.error("Error al parsear producto:", err);
          }
        };
      });
    } catch (err) {
      console.error("Error cargando productos:", err);
      listaProductosPedido.innerHTML =
        '<div class="text-center py-4 text-danger small">Ocurrió un error al cargar los productos.</div>';
    } finally {
      listaProductosPedido.classList.remove("is-loading");
    }
  }

  // Paso 2: Configurar producto seleccionado en el modal
  function seleccionarProductoYConfigurar(prod) {
    estadoSelector.productoSeleccionado = prod;

    // Ocultar selector temporalmente
    if (modalSelector) modalSelector.hide();

    // Llenar datos en el modal de configuración
    if (configProductoImg) configProductoImg.src = prod.imagen_url || "/static/img/default.webp";
    if (configProductoNombre) configProductoNombre.textContent = prod.nombre;
    if (configProductoSku) configProductoSku.textContent = prod.codigo_sku ? `SKU: ${prod.codigo_sku}` : "Sin SKU";
    if (configProductoStock) configProductoStock.textContent = prod.stock_disponible;
    if (configProductoUnidad) configProductoUnidad.textContent = prod.unidad || "ud";

    // Configurar precio
    if (puedeModificarPrecio && modalInputPrecio) {
      modalInputPrecio.value = prod.precio.toFixed(2);
      modalInputPrecio.min = prod.precio_min !== null ? prod.precio_min : 0.01;
      if (prod.precio_max !== null) {
        modalInputPrecio.max = prod.precio_max;
        if (helperPrecioLimites) {
          helperPrecioLimites.textContent = `Límites permitidos: Mín ${monedaSimbolo} ${prod.precio_min ? prod.precio_min.toFixed(2) : "0.01"} / Máx ${monedaSimbolo} ${prod.precio_max.toFixed(2)}`;
          helperPrecioLimites.style.display = "block";
        }
      } else if (prod.precio_min !== null) {
        modalInputPrecio.removeAttribute("max");
        if (helperPrecioLimites) {
          helperPrecioLimites.textContent = `Precio mínimo permitido: ${monedaSimbolo} ${prod.precio_min.toFixed(2)}`;
          helperPrecioLimites.style.display = "block";
        }
      } else {
        modalInputPrecio.removeAttribute("max");
        if (helperPrecioLimites) helperPrecioLimites.style.display = "none";
      }
    } else {
      if (modalInputPrecio) modalInputPrecio.value = `${prod.precio.toFixed(2)}`;
      if (modalHiddenPrecio) modalHiddenPrecio.value = prod.precio.toFixed(2);
    }

    // Configurar cantidad
    if (modalInputCantidad) {
      modalInputCantidad.max = prod.stock_disponible;
      modalInputCantidad.min = 1;
      modalInputCantidad.step = "any";
    }

    if (estadoSelector.modo === "cambiar") {
      if (tituloConfigurarProducto) {
        tituloConfigurarProducto.innerHTML = '<i class="bx bx-sync me-1"></i> Cambiar Producto';
      }
      if (formConfirmarProductoPedido) {
        formConfirmarProductoPedido.action = urlCambiarBase;
      }
      if (configDetalleId) configDetalleId.value = estadoSelector.detalleId;
      if (configProductoIdCambio) configProductoIdCambio.value = prod.id;
      if (configProductoIdAnexo) configProductoIdAnexo.value = "";
      if (modalInputCantidad) modalInputCantidad.name = "cantidad_cambio";

      // Sugerir la cantidad que solicitó el cliente si hay stock suficiente (mínimo 1)
      const cantOrig = parseFloat(estadoSelector.cantidadOriginal) || 1;
      if (modalInputCantidad) {
        modalInputCantidad.value = Math.max(1, Math.min(cantOrig, prod.stock_disponible));
      }

      // Ficha del producto original
      if (nombreProductoOriginalCambio) nombreProductoOriginalCambio.textContent = estadoSelector.nombreOriginal;
      if (imgProductoOriginalCambio) imgProductoOriginalCambio.src = estadoSelector.imagenOriginal || "/static/img/default.webp";
      if (cantProductoOriginalCambio) cantProductoOriginalCambio.textContent = `${estadoSelector.cantidadOriginal} ud`;
      if (bloqueProductoOriginalCambio) bloqueProductoOriginalCambio.style.display = "block";
      if (boxProductoOriginalCambio) boxProductoOriginalCambio.style.display = "block";
      if (boxProductoNuevoSustituto) boxProductoNuevoSustituto.style.display = "flex";
      if (boxProductoSeleccionado) boxProductoSeleccionado.classList.add("producto-elegido-card--cambio");

      // Justificación obligatoria para cambio
      if (divJustificacionCambio) divJustificacionCambio.style.display = "block";
      if (modalInputJustificacion) {
        modalInputJustificacion.required = true;
        modalInputJustificacion.value = "";
      }

      if (btnConfirmarProducto) {
        btnConfirmarProducto.innerHTML = '<i class="bx bx-sync"></i> Confirmar cambio';
      }
    } else {
      if (tituloConfigurarProducto) {
        tituloConfigurarProducto.innerHTML = '<i class="bx bx-plus-circle me-1"></i> Anexar Producto';
      }
      if (formConfirmarProductoPedido) {
        formConfirmarProductoPedido.action = urlAnexarBase;
      }
      if (configDetalleId) configDetalleId.value = "";
      if (configProductoIdCambio) configProductoIdCambio.value = "";
      if (configProductoIdAnexo) configProductoIdAnexo.value = prod.id;
      if (modalInputCantidad) {
        modalInputCantidad.name = "cantidad";
        modalInputCantidad.value = "1";
      }

      if (bloqueProductoOriginalCambio) bloqueProductoOriginalCambio.style.display = "none";
      if (boxProductoOriginalCambio) boxProductoOriginalCambio.style.display = "none";
      if (boxProductoNuevoSustituto) boxProductoNuevoSustituto.style.display = "none";
      if (boxProductoSeleccionado) boxProductoSeleccionado.classList.remove("producto-elegido-card--cambio");
      if (divJustificacionCambio) divJustificacionCambio.style.display = "none";
      if (modalInputJustificacion) {
        modalInputJustificacion.required = false;
        modalInputJustificacion.value = "";
      }

      if (btnConfirmarProducto) {
        btnConfirmarProducto.innerHTML = '<i class="bx bx-plus"></i> Anexar producto';
      }
    }

    actualizarSubtotalEstimado();

    // Abrir modal de configuración
    if (modalConfig) {
      setTimeout(() => modalConfig.show(), 200);
    }
  }

  // Botón volver al selector desde la configuración
  if (btnVolverAlSelector) {
    btnVolverAlSelector.onclick = () => {
      if (modalConfig) modalConfig.hide();
      setTimeout(() => {
        if (modalSelector) modalSelector.show();
      }, 200);
    };
  }

  // Stepper: Disminuir cantidad
  if (btnQtyDisminuir) {
    btnQtyDisminuir.onclick = () => {
      let val = parseFloat(modalInputCantidad.value) || 1;
      if (val > 1) {
        val = Math.floor(val - 1);
      } else {
        val = 1;
      }
      modalInputCantidad.value = val;
      actualizarSubtotalEstimado();
    };
  }

  // Stepper: Aumentar cantidad
  if (btnQtyAumentar) {
    btnQtyAumentar.onclick = () => {
      let val = parseFloat(modalInputCantidad.value) || 0;
      const maxStock =
        parseFloat(estadoSelector.productoSeleccionado?.stock_disponible) || 999999;
      if (val + 1 <= maxStock) {
        modalInputCantidad.value = Math.floor(val + 1);
      } else if (val < maxStock) {
        modalInputCantidad.value = maxStock;
      } else {
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Stock máximo alcanzado",
            text: `No hay más de ${maxStock} unidades disponibles de este producto.`,
            icon: "warning",
            confirmButtonText: "Entendido",
            customClass: { confirmButton: "classbotones" },
          });
        }
      }
      actualizarSubtotalEstimado();
    };
  }

  // Escribir directamente en el campo de cantidad
  if (modalInputCantidad) {
    modalInputCantidad.addEventListener("input", () => {
      actualizarSubtotalEstimado();
    });
    modalInputCantidad.addEventListener("change", () => {
      let val = parseFloat(modalInputCantidad.value);
      const maxStock =
        parseFloat(estadoSelector.productoSeleccionado?.stock_disponible) || 999999;
      if (isNaN(val) || val < 1) {
        modalInputCantidad.value = 1;
      } else if (val > maxStock) {
        modalInputCantidad.value = maxStock;
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Cantidad ajustada al stock",
            text: `La cantidad se ajustó al stock disponible (${maxStock} ud).`,
            icon: "warning",
            confirmButtonText: "Entendido",
            customClass: { confirmButton: "classbotones" },
          });
        }
      }
      actualizarSubtotalEstimado();
    });
  }

  // Escribir en el campo de precio (si tiene permiso)
  if (modalInputPrecio && puedeModificarPrecio) {
    modalInputPrecio.addEventListener("input", actualizarSubtotalEstimado);
  }

  // Botón abrir selector para ANEXAR
  const btnAbrirAnexarPedido = document.getElementById("btnAbrirAnexarPedido");
  if (btnAbrirAnexarPedido) {
    btnAbrirAnexarPedido.onclick = () => {
      estadoSelector.modo = "anexar";
      estadoSelector.detalleId = null;
      estadoSelector.nombreOriginal = "";
      estadoSelector.cantidadOriginal = "";
      estadoSelector.busqueda = "";
      if (inputBuscarProductosPedido) inputBuscarProductosPedido.value = "";
      const tit = document.getElementById("tituloSelectorPedido");
      if (tit) tit.textContent = "Seleccionar producto para anexar";
      if (modalSelector) modalSelector.show();
      cargarCatalogo(1);
    };
  }

  // Botones abrir selector para CAMBIAR producto
  document.querySelectorAll(".btn-abrir-cambio-pedido").forEach((btn) => {
    btn.onclick = () => {
      estadoSelector.modo = "cambiar";
      estadoSelector.detalleId = btn.dataset.detalleId;
      estadoSelector.nombreOriginal = btn.dataset.nombre || "";
      estadoSelector.cantidadOriginal = btn.dataset.cantidad || "1";
      estadoSelector.imagenOriginal = btn.dataset.imagen || "/static/img/default.webp";
      estadoSelector.busqueda = "";
      if (inputBuscarProductosPedido) inputBuscarProductosPedido.value = "";
      const tit = document.getElementById("tituloSelectorPedido");
      if (tit) {
        tit.textContent = `Seleccionar sustituto para: ${estadoSelector.nombreOriginal}`;
      }
      if (modalSelector) modalSelector.show();
      cargarCatalogo(1);
    };
  });

  // Formulario de búsqueda en el catálogo
  if (formBuscarProductosPedido) {
    formBuscarProductosPedido.onsubmit = (e) => {
      e.preventDefault();
      estadoSelector.busqueda = (inputBuscarProductosPedido?.value || "").trim();
      cargarCatalogo(1);
    };
  }
  if (inputBuscarProductosPedido) {
    let debounceTimer;
    inputBuscarProductosPedido.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        estadoSelector.busqueda = inputBuscarProductosPedido.value.trim();
        cargarCatalogo(1);
      }, 320);
    });
  }

  // Validación previa al enviar formConfirmarProductoPedido
  if (formConfirmarProductoPedido) {
    formConfirmarProductoPedido.onsubmit = (e) => {
      const prodId =
        estadoSelector.modo === "cambiar"
          ? configProductoIdCambio.value
          : configProductoIdAnexo.value;

      if (!prodId) {
        e.preventDefault();
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Producto requerido",
            text: "No se ha seleccionado ningún producto.",
            icon: "warning",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          });
        }
        return;
      }

      const cant = parseFloat(modalInputCantidad.value);
      if (isNaN(cant) || cant <= 0) {
        e.preventDefault();
        alert("Por favor ingresa una cantidad válida mayor a 0.");
        return;
      }

      if (
        estadoSelector.modo === "cambiar" &&
        !modalInputJustificacion.value.trim()
      ) {
        e.preventDefault();
        if (typeof Swal !== "undefined") {
          Swal.fire({
            title: "Justificación obligatoria",
            text: "Debes escribir el motivo del cambio de producto.",
            icon: "warning",
            confirmButtonText: "Entendido",
            customClass: { confirmButton: "classbotones" },
          });
        } else {
          alert("Debes escribir el motivo del cambio.");
        }
        modalInputJustificacion.focus();
      }
    };
  }

  // ========================================================
  // CONFIRMACIONES SWEETALERT PARA FORMULARIOS DE REVISIÓN
  // ========================================================
  const confirmaciones = {
    aceptar_todos: () => ({
      title: "¿Confirmar todos los productos pendientes?",
      text: "Se aceptarán únicamente los productos que aún no han sido revisados.",
      confirmButtonText: "Sí, confirmar todo",
      icon: "question",
    }),
    aceptar: (form) =>
      form.id === "formAceptarPedidoCompleto"
        ? {
            title: "¿Aceptar pedido?",
            text: `El pedido quedará listo para cobro en caja por un total de ${
              form.querySelector("#btnAceptarPedidoCompleto")?.dataset.total || ""
            }.`,
            confirmButtonText: "Sí, aceptar pedido",
            icon: "question",
          }
        : {
            title: "¿Aceptar producto?",
            text: `¿Deseas aceptar ${form.dataset.cantidad || ""} unidades de ${
              form.dataset.nombre || "este producto"
            }?`,
            confirmButtonText: "Sí, aceptar",
            icon: "question",
          },
    ajustar: (form) => ({
      title: "¿Guardar el cambio de cantidad?",
      text: `Se actualizarán a ${
        form.querySelector("input[name='nueva_cantidad']")?.value ||
        "la nueva cantidad"
      } las unidades aprobadas de ${form.dataset.nombre || "este producto"}.`,
      confirmButtonText: "Sí, guardar cambio",
      icon: "question",
    }),
    rechazar: (form) =>
      form.id === "formRechazarPedidoCompleto"
        ? {
            title: "¿Rechazar pedido completo?",
            text: "Todas las unidades reservadas por este pedido se liberarán.",
            confirmButtonText: "Sí, rechazar pedido",
            icon: "warning",
            confirmButtonColor: "#dc2626",
          }
        : {
            title: "¿Rechazar producto?",
            text: `Se rechazará ${
              form.dataset.nombre || "este producto"
            } y se liberará su reserva.`,
            confirmButtonText: "Sí, rechazar producto",
            icon: "warning",
            confirmButtonColor: "#dc2626",
          },
    devolver: (form) => ({
      title: "¿Devolver producto?",
      text: `Se devolverán ${form.dataset.cantidad || ""} unidades de ${
        form.dataset.nombre || "este producto"
      }.`,
      confirmButtonText: "Sí, devolver producto",
      icon: "warning",
      confirmButtonColor: "#dc2626",
    }),
    entregar: () => ({
      title: "¿Entregar el pedido?",
      text: "El pedido ya fue pagado en caja. Al confirmar, pasará a estado Entregado.",
      confirmButtonText: "Sí, entregar pedido",
      icon: "question",
    }),
  };

  document
    .querySelectorAll(".pedido-manager-detalle form[method='post']")
    .forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (form.dataset.confirmed === "true") return;
        const accion = form.querySelector("input[name='accion']")?.value;
        const crearConfirmacion = confirmaciones[accion];
        if (!crearConfirmacion) return;

        event.preventDefault();
        const opciones = crearConfirmacion(form);
        const submitForm = () => {
          form.dataset.confirmed = "true";
          form.requestSubmit();
        };

        if (typeof Swal !== "undefined") {
          Swal.fire({
            ...opciones,
            showCancelButton: true,
            cancelButtonText: "Cancelar",
            confirmButtonColor:
              opciones.confirmButtonColor ||
              getComputedStyle(document.body)
                .getPropertyValue("--system-primary")
                .trim() ||
              "#32877f",
            cancelButtonColor: "#64748b",
          }).then((result) => {
            if (result.isConfirmed) submitForm();
          });
        } else if (confirm(`${opciones.title} ${opciones.text}`)) {
          submitForm();
        }
      });
    });

  // Mensajes Flash
  const mensajes = document.querySelectorAll(
    "[data-pedido-flash-messages] [data-message]"
  );
  for (const mensaje of mensajes) {
    const tipo = mensaje.dataset.type.split(" ");
    const icon = tipo.includes("success")
      ? "success"
      : tipo.includes("error")
      ? "error"
      : tipo.includes("warning")
      ? "warning"
      : "info";
    const title = {
      success: "Éxito",
      error: "No se pudo completar",
      warning: "Aviso",
      info: "Información",
    }[icon];

    if (typeof Swal !== "undefined") {
      await Swal.fire({
        title,
        text: mensaje.dataset.message,
        icon,
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
    } else {
      window.alert(mensaje.dataset.message);
    }
  }
});