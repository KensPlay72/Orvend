document.addEventListener("DOMContentLoaded", () => {
  const app = document.getElementById("devolucionesVentaApp");
  if (!app) return;

  const buscadoresFactura = [
    {
      form: document.getElementById("buscarFacturaForm"),
      input: document.getElementById("numeroFactura"),
    },
    {
      form: document.getElementById("buscarFacturaFormMovil"),
      input: document.getElementById("numeroFacturaMovil"),
    },
  ].filter(({ form, input }) => form && input);
  const resultado = document.getElementById("resultadoFactura");
  const cuerpoProductos = document.getElementById("productosFacturaBody");
  const botonTodo = document.getElementById("seleccionarTodo");
  const botonAbrirModal = document.getElementById("abrirModalDevolucion");
  const botonCrear = document.getElementById("crearDevolucion");
  const modalDevolucion = new bootstrap.Modal(
    document.getElementById("modalDevolucionVenta"),
  );
  let facturaActual = null;

  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  buscadoresFactura.forEach(({ input }) => {
    input.addEventListener("input", () => {
      input.value = input.value.replace(/\D/g, "");
    });
  });
  const escapeHtml = (valor) =>
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

  const mostrarError = (mensaje) =>
    Swal.fire({
      title: "Error",
      text: mensaje,
      icon: "error",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });

  const leerRespuestaJson = async (respuesta) => {
    const contenido = await respuesta.text();
    try {
      return JSON.parse(contenido);
    } catch (_) {
      if (respuesta.redirected || respuesta.status === 401)
        throw new Error("Tu sesión ya no está disponible. Inicia sesión nuevamente.");
      if (respuesta.status === 403)
        throw new Error("No tienes permiso para realizar esta operación.");
      if (respuesta.status === 404)
        throw new Error("No se encontró la factura solicitada.");
      throw new Error("El servidor no pudo procesar la solicitud. Inténtalo nuevamente.");
    }
  };

  function obtenerDetallesSeleccionados() {
    return Array.from(cuerpoProductos.querySelectorAll("tr"))
      .filter((fila) => fila.querySelector(".dv-seleccionar").checked)
      .map((fila) => ({
        detalleVentaId: Number(fila.dataset.detalleId),
        cantidad: fila.querySelector(".dv-cantidad-input").value,
      }))
      .filter((detalle) => Number(detalle.cantidad) > 0);
  }

  function actualizarInputsFila(fila) {
    const checkbox = fila.querySelector(".dv-seleccionar");
    const input = fila.querySelector(".dv-cantidad-input");
    input.disabled = !checkbox.checked;
    if (!checkbox.checked) input.value = "0";
    fila.classList.toggle("dv-fila-seleccionada", checkbox.checked);
  }

  function seleccionarFila(fila, seleccionada, usarDisponible = false) {
    const checkbox = fila.querySelector(".dv-seleccionar");
    const input = fila.querySelector(".dv-cantidad-input");
    if (checkbox.disabled) return;
    checkbox.checked = seleccionada;
    if (seleccionada && usarDisponible) input.value = fila.dataset.disponible;
    actualizarInputsFila(fila);
  }

  function actualizarEstadoBotonTodo() {
    const filasSeleccionables = Array.from(
      cuerpoProductos.querySelectorAll("tr"),
    ).filter((fila) => !fila.querySelector(".dv-seleccionar").disabled);
    const todoSeleccionado =
      filasSeleccionables.length > 0 &&
      filasSeleccionables.every(
        (fila) => fila.querySelector(".dv-seleccionar").checked,
      );

    botonTodo.classList.toggle("btn-success", todoSeleccionado);
    botonTodo.classList.toggle("btn-outline-success", !todoSeleccionado);
    botonTodo.setAttribute("aria-pressed", String(todoSeleccionado));
    botonTodo.innerHTML = todoSeleccionado
      ? '<i class="bx bx-x"></i> Quitar selección'
      : '<i class="bx bx-check-double"></i> Toda la factura';
  }

  function renderFactura(data) {
    facturaActual = data.factura;
    document.getElementById("facturaNumero").textContent =
      `#${data.factura.numero}`;
    document.getElementById("facturaFecha").textContent = data.factura.fecha;
    document.getElementById("facturaCliente").textContent = data.factura.cliente
      .id
      ? `${data.factura.cliente.id} | ${data.factura.cliente.nombre}`
      : data.factura.cliente.nombre;
    document.getElementById("facturaSucursal").textContent =
      data.factura.sucursal;
    document.getElementById("facturaTipoVenta").textContent =
      data.factura.tipoVentaTexto;
    const esCredito = data.factura.tipoVenta === "credito";
    document
      .getElementById("resolucionCredito")
      .classList.toggle("d-none", !esCredito);
    document.getElementById("resolucionDevolucion").value = esCredito
      ? ""
      : "NOTA_CREDITO";
    document
      .querySelectorAll(".resolucion-credito-btn")
      .forEach((boton) => boton.classList.remove("active"));

    cuerpoProductos.innerHTML = data.detalles
      .map((detalle) => {
        const disponible = Number(detalle.cantidadDisponible);
        const sinDisponible = disponible <= 0;
        return `
        <tr data-detalle-id="${detalle.detalleVentaId}" data-disponible="${detalle.cantidadDisponible}">
          <td data-label="Seleccionar" class="dv-seleccion-celda"><input type="checkbox" class="form-check-input dv-seleccionar" ${sinDisponible ? "disabled" : ""}></td>
          <td data-label="Producto" class="dv-producto-celda">${escapeHtml(detalle.producto)}</td>
          <td data-label="Vendido">${detalle.cantidadVendida}</td>
          <td data-label="Devuelto">${detalle.cantidadDevuelta}</td>
          <td data-label="Disponible">${detalle.cantidadDisponible}</td>
          <td data-label="Precio unitario">${window.MONEDA_SISTEMA || "L."} ${Number(detalle.precioUnitario).toFixed(2)}</td>
          <td data-label="Cantidad a devolver" class="dv-cantidad-celda"><input type="number" inputmode="decimal" class="form-control dv-cantidad-input" min="0.01" step="0.01" max="${detalle.cantidadDisponible}" value="0" disabled ${sinDisponible ? "" : ""}></td>
        </tr>`;
      })
      .join("");

    actualizarEstadoBotonTodo();
    resultado.classList.remove("d-none");
    document.getElementById("motivoDevolucion").value = "";
    document.getElementById("justificacionDevolucion").value = "";
  }

  async function buscarFactura(numero) {
    if (!numero) return;
    if (!/^\d+$/.test(numero)) {
      mostrarError("Ingresa únicamente el número de factura.");
      return;
    }

    try {
      const respuesta = await fetch(
        `${app.dataset.baseUrl}factura/${encodeURIComponent(numero)}/`,
      );
      const data = await leerRespuestaJson(respuesta);
      if (!respuesta.ok || !data.success)
        throw new Error(data.message || "No se pudo consultar la factura");
      renderFactura(data);
    } catch (error) {
      resultado.classList.add("d-none");
      mostrarError(error.message);
    }
  }

  buscadoresFactura.forEach(({ form, input }) => {
    form.addEventListener("submit", (evento) => {
      evento.preventDefault();
      buscarFactura(input.value.trim());
    });
  });

  cuerpoProductos.addEventListener("change", (evento) => {
    if (evento.target.classList.contains("dv-seleccionar")) {
      actualizarInputsFila(evento.target.closest("tr"));
      actualizarEstadoBotonTodo();
    }
  });

  cuerpoProductos.addEventListener("click", (evento) => {
    if (evento.target.closest("input, button, a, label")) return;
    const fila = evento.target.closest("tr");
    if (!fila) return;
    const checkbox = fila.querySelector(".dv-seleccionar");
    seleccionarFila(fila, !checkbox.checked);
    actualizarEstadoBotonTodo();
  });

  cuerpoProductos.addEventListener("input", (evento) => {
    if (!evento.target.classList.contains("dv-cantidad-input")) return;
    const maximo = Number(evento.target.max);
    if (Number(evento.target.value) > maximo) evento.target.value = maximo;
    if (Number(evento.target.value) < 0) evento.target.value = 0;
  });

  cuerpoProductos.addEventListener(
    "wheel",
    (evento) => {
      if (
        evento.target.classList.contains("dv-cantidad-input") &&
        window.matchMedia("(min-width: 1033px)").matches
      ) {
        evento.preventDefault();
      }
    },
    { passive: false },
  );

  botonTodo.addEventListener("click", () => {
    const filasSeleccionables = Array.from(
      cuerpoProductos.querySelectorAll("tr"),
    ).filter((fila) => !fila.querySelector(".dv-seleccionar").disabled);
    const todoSeleccionado =
      filasSeleccionables.length > 0 &&
      filasSeleccionables.every(
        (fila) => fila.querySelector(".dv-seleccionar").checked,
      );

    filasSeleccionables.forEach((fila) =>
      seleccionarFila(fila, !todoSeleccionado, !todoSeleccionado),
    );
    actualizarEstadoBotonTodo();
  });

  botonAbrirModal.addEventListener("click", () => {
    if (!obtenerDetallesSeleccionados().length) {
      mostrarError("Seleccione al menos un producto y su cantidad");
      return;
    }
    modalDevolucion.show();
  });

  document.querySelectorAll(".resolucion-credito-btn").forEach((boton) => {
    boton.addEventListener("click", () => {
      document.getElementById("resolucionDevolucion").value =
        boton.dataset.resolucion;
      document
        .querySelectorAll(".resolucion-credito-btn")
        .forEach((item) => item.classList.remove("active"));
      boton.classList.add("active");
    });
  });

  botonCrear.addEventListener("click", async () => {
    const motivo = document.getElementById("motivoDevolucion").value;
    const justificacion = document
      .getElementById("justificacionDevolucion")
      .value.trim();
    const resolucion = document.getElementById("resolucionDevolucion").value;
    const detalles = obtenerDetallesSeleccionados();

    if (!detalles.length)
      return mostrarError("Seleccione al menos un producto y su cantidad");
    if (!motivo || !justificacion)
      return mostrarError("Seleccione el motivo e ingrese una justificación");
    if (facturaActual.tipoVenta === "credito" && !resolucion)
      return mostrarError(
        "Seleccione si desea generar nota de crédito o deducir el saldo pendiente",
      );

    botonCrear.disabled = true;
    botonCrear.innerHTML =
      '<i class="bx bx-loader-alt bx-spin"></i> Generando...';

    try {
      const respuesta = await fetch(app.dataset.crearUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          facturaId: facturaActual.id,
          motivo,
          justificacion,
          resolucion,
          detalles,
        }),
      });
      const data = await leerRespuestaJson(respuesta);
      if (!respuesta.ok || !data.success)
        throw new Error(data.message || "No se pudo crear la devolución");

      await Swal.fire({
        title:
          data.resolucion === "DEDUCIR_SALDO"
            ? "Saldo deducido"
            : "Nota de crédito generada",
        html:
          data.resolucion === "DEDUCIR_SALDO"
            ? `Se registró un abono a la factura.<br>Monto: ${window.MONEDA_SISTEMA || "L."} ${Number(data.monto).toFixed(2)}`
            : `<strong>${escapeHtml(data.notaCredito)}</strong><br>Monto: ${window.MONEDA_SISTEMA || "L."} ${Number(data.monto).toFixed(2)}`,
        icon: "success",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
      window.location.reload();
    } catch (error) {
      mostrarError(error.message);
    } finally {
      botonCrear.disabled = false;
      botonCrear.innerHTML =
        '<i class="bx bx-credit-card"></i> Generar nota de crédito';
    }
  });
});
