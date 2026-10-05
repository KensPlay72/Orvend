document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#tablaDevolucion tbody tr").forEach((fila) => {
    fila.addEventListener("click", (event) => {
      // Los controles propios de la fila conservan su interacción normal.
      if (event.target.closest("input, select, button, textarea, label, a")) return;
      const check = fila.querySelector(".check-devolucion");
      if (!check) return;
      check.checked = !check.checked;
      check.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });

  const botonDevolucion = document.getElementById("enviarDevolucionBtn");
  if (botonDevolucion) {
    botonDevolucion.addEventListener("click", async () => {
      const productos = [];

      document.querySelectorAll("#tablaDevolucion tbody tr").forEach((fila) => {
        if (!fila.querySelector(".check-devolucion")?.checked) return;

        const motivo = fila.querySelector(".motivo-select").value;
        if (!motivo) return;
        const producto = {
          ProductoId: Number(fila.querySelector(".producto-id").value),
          Motivo: Number(motivo),
        };
        if (fila.classList.contains("es-convertido")) {
          const cantidadHijo = fila.querySelector(".cantidad-hijo");
          const maximo = Number(fila.dataset.maximoHijo || 0);
          const cantidad = Number(cantidadHijo?.value || 0);
          if (!fila.dataset.productoHijoId || !cantidad || cantidad > maximo) return;
          producto.ProductoHijoId = Number(fila.dataset.productoHijoId);
          producto.CantidadHijo = Number(cantidadHijo.value);
        } else {
          producto.Cantidad = Number(fila.dataset.cantidadOriginal || fila.children[3].innerText);
        }
        productos.push(producto);
      });

      const seleccionados = document.querySelectorAll(
        "#tablaDevolucion .check-devolucion:checked",
      ).length;
      if (!seleccionados || productos.length !== seleccionados) {
        Swal.fire("Datos incompletos", "Selecciona productos, indica el motivo y, si convertiste una presentación, la cantidad de unidades a devolver.", "warning");
        return;
      }

      try {
        const respuesta = await fetch("/manager/bodega/devocompras/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
          },
          body: JSON.stringify({
            CompraId: Number(document.getElementById("entrada-id").value),
            Observaciones: document.getElementById("observaciones").value.trim(),
            Productos: productos,
          }),
        });

        if (!respuesta.ok) {
          const error = await respuesta.json();
          throw new Error(error.message || "No se pudo registrar la devolución.");
        }

        const pdf = await respuesta.blob();
        await Swal.fire({
          icon: "success",
          title: "Devolución registrada",
          text: "La devolución se procesó correctamente. A continuación se descargará la nota de devolución.",
          confirmButtonText: "Descargar nota",
          customClass: { confirmButton: "classbotones" },
        });

        const enlace = document.createElement("a");
        enlace.href = URL.createObjectURL(pdf);
        enlace.download = "DevolucionCompra.pdf";
        document.body.append(enlace);
        enlace.click();
        enlace.remove();
        URL.revokeObjectURL(enlace.href);
        window.location.href = "/manager/bodega/recepcion_inventario/";
      } catch (error) {
        Swal.fire("Error", error.message || "No se pudo registrar la devolución.", "error");
      }
    });
  }

  const modalHijos = document.getElementById("modalHijosDevolucion");
  const listaHijos = document.getElementById("listaHijosDevolucion");
  const modalDevolucion = document.getElementById("devo");
  const listaDevolucionMovil = document.getElementById("listaDevolucionModalMovil");
  let volverADevolucion = false;

  const escaparHtml = (valor) => String(valor ?? "").replace(/[&<>'"]/g, (caracter) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#039;",
    '"': "&quot;",
  })[caracter]);

  const construirTarjetasDevolucionMovil = () => {
    if (!listaDevolucionMovil) return;

    const filas = Array.from(document.querySelectorAll("#tablaDevolucion tbody tr"));
    listaDevolucionMovil.innerHTML = "";

    filas.forEach((fila, indice) => {
      const nombre = fila.querySelector(".nombre-devolucion")?.textContent.trim() || "Producto";
      const sku = fila.querySelector(".sku-devolucion")?.textContent.trim() || "Sin SKU";
      const cantidad = fila.querySelector(".cantidad-devolucion")?.textContent.trim() || "0";
      const motivo = fila.querySelector(".motivo-select");
      const convertir = fila.querySelector(".convertir-hijo-btn");
      const convertido = fila.classList.contains("es-convertido");
      const cantidadHijo = fila.querySelector(".cantidad-hijo");

      const tarjeta = document.createElement("article");
      tarjeta.className = "recepcion-mobile-card modal-devolucion-mobile-card";
      tarjeta.innerHTML = `
        <header class="recepcion-mobile-card__header">
          <div class="recepcion-mobile-card__registro">
            <span class="recepcion-mobile-card__icon"><i class="bx bx-package" aria-hidden="true"></i></span>
            <span><small>Producto ${indice + 1}</small><strong>${escaparHtml(nombre)}</strong></span>
          </div>
          <div class="recepcion-mobile-card__estado"><span class="badge bg-warning text-dark">${escaparHtml(cantidad)} ud.</span></div>
        </header>
        <div class="recepcion-mobile-card__origen">
          <span class="recepcion-mobile-card__origen-icon"><i class="bx bx-barcode" aria-hidden="true"></i></span>
          <div><small>SKU</small><strong>${escaparHtml(sku)}</strong></div>
          <span class="recepcion-mobile-card__tipo"><span class="badge bg-primary">Devolución</span></span>
        </div>
        <div class="recepcion-mobile-card__meta">
          <div><i class="bx bx-package"></i><span><small>Cantidad</small><strong>${escaparHtml(cantidad)}</strong></span></div>
          <div><i class="bx bx-check-square"></i><span><small>Estado</small><strong>${convertido ? "Convertido" : "Unidad original"}</strong></span></div>
        </div>
        <div class="modal-devolucion-mobile-card__controles">
          <label class="modal-devolucion-mobile-card__seleccion"><input type="checkbox" ${fila.querySelector(".check-devolucion")?.checked ? "checked" : ""}> Seleccionar producto</label>
          <select class="form-select modal-devolucion-mobile-card__motivo">${motivo?.innerHTML || ""}</select>
          ${convertir && !convertir.classList.contains("d-none") ? '<button type="button" class="btn btn-outline-success modal-devolucion-mobile-card__convertir"><i class="bx bx-transfer-alt"></i> Convertir a unidad</button>' : ""}
          ${convertido ? `<input type="text" inputmode="numeric" class="form-control modal-devolucion-mobile-card__cantidad-hijo" value="${escaparHtml(cantidadHijo?.value || "")}" placeholder="Cantidad a devolver">` : ""}
        </div>`;

      const checkOriginal = fila.querySelector(".check-devolucion");
      const checkMovil = tarjeta.querySelector("input[type=checkbox]");
      const motivoMovil = tarjeta.querySelector(".modal-devolucion-mobile-card__motivo");
      if (motivoMovil && motivo) motivoMovil.value = motivo.value;
      checkMovil?.addEventListener("change", () => { checkOriginal.checked = checkMovil.checked; });
      motivoMovil?.addEventListener("change", () => { motivo.value = motivoMovil.value; });
      tarjeta.querySelector(".modal-devolucion-mobile-card__convertir")?.addEventListener("click", () => convertir.click());
      tarjeta.querySelector(".modal-devolucion-mobile-card__cantidad-hijo")?.addEventListener("input", (evento) => {
        cantidadHijo.value = evento.target.value;
        cantidadHijo.dispatchEvent(new Event("input", { bubbles: true }));
        evento.target.value = cantidadHijo.value;
      });
      listaDevolucionMovil.appendChild(tarjeta);
    });
  };

  modalDevolucion?.addEventListener("show.bs.modal", construirTarjetasDevolucionMovil);
  document.addEventListener("devolucion:hijo-seleccionado", construirTarjetasDevolucionMovil);

  // Evita modales encimados: el selector de hijos toma el lugar temporalmente
  // de la devolución y esta vuelve a mostrarse al terminar o cancelarlo.
  modalHijos?.addEventListener("hidden.bs.modal", () => {
    if (!volverADevolucion || !modalDevolucion) return;

    volverADevolucion = false;
    bootstrap.Modal.getOrCreateInstance(modalDevolucion).show();
  });

  document.querySelectorAll("#tablaDevolucion tbody tr").forEach((fila) => {
    fila.dataset.cantidadOriginal = fila.querySelector(".cantidad-devolucion")?.textContent.trim() || "0";
    const camposHijo = fila.querySelector(".devolucion-hijo-campos");
    const selectHijo = fila.querySelector(".hijo-select");
    const cantidadHijo = fila.querySelector(".cantidad-hijo");
    const ayuda = fila.querySelector(".equivalencia-hijo");
    const botonConvertir = fila.querySelector(".convertir-hijo-btn");
    if (!camposHijo || !selectHijo || !cantidadHijo || !botonConvertir) return;

    botonConvertir.addEventListener("click", () => {
      listaHijos.innerHTML = "";
      Array.from(selectHijo.options).forEach((opcion) => {
        const botonHijo = document.createElement("button");
        botonHijo.type = "button";
        botonHijo.className = "hijo-devolucion-option";
        botonHijo.innerHTML = `<span class="hijo-devolucion-option__icon"><i class="bx bx-package"></i></span><span class="hijo-devolucion-option__info"><strong>${opcion.textContent}</strong><span>SKU: ${opcion.dataset.sku}</span></span><span class="hijo-devolucion-option__state">${opcion.dataset.maximo} unidades</span>`;
        botonHijo.addEventListener("click", () => seleccionarProductoHijo(fila, opcion));
        listaHijos.appendChild(botonHijo);
      });
      let selectorAbierto = false;
      const mostrarSelectorHijos = () => {
        if (selectorAbierto) return;
        selectorAbierto = true;
        bootstrap.Modal.getOrCreateInstance(modalHijos).show();
      };

      volverADevolucion = true;
      const instanciaDevolucion = modalDevolucion
        ? bootstrap.Modal.getOrCreateInstance(modalDevolucion)
        : null;

      if (modalDevolucion?.classList.contains("show") && instanciaDevolucion) {
        modalDevolucion.addEventListener("hidden.bs.modal", mostrarSelectorHijos, {
          once: true,
        });
        instanciaDevolucion.hide();
      } else {
        mostrarSelectorHijos();
      }
    });

    cantidadHijo.addEventListener("input", () => {
      cantidadHijo.value = cantidadHijo.value.replace(/[^0-9.]/g, "");
      const maximo = Number(fila.dataset.maximoHijo || 0);
      if (maximo && Number(cantidadHijo.value) > maximo) cantidadHijo.value = maximo;
    });
  });

  function seleccionarProductoHijo(fila, opcion) {
    const maximo = Number(opcion.dataset.maximo || 0);
    const equivalencia = Number(opcion.dataset.equivalencia || 0);
    fila.classList.add("es-convertido");
    fila.dataset.productoHijoId = opcion.value;
    fila.dataset.maximoHijo = String(maximo);
    fila.querySelector(".nombre-devolucion").textContent = opcion.textContent.trim();
    fila.querySelector(".sku-devolucion").textContent = opcion.dataset.sku || "N/A";
    fila.querySelector(".cantidad-devolucion").textContent = maximo;
    fila.querySelector(".check-devolucion").checked = true;
    fila.querySelector(".convertir-hijo-btn").classList.add("d-none");
    const camposHijo = fila.querySelector(".devolucion-hijo-campos");
    const cantidadHijo = fila.querySelector(".cantidad-hijo");
    camposHijo.classList.remove("d-none");
    cantidadHijo.value = "";
    cantidadHijo.focus();
    fila.querySelector(".equivalencia-hijo").textContent = `Total convertido: ${maximo} unidades (Valor: ${equivalencia}).`;
    document.dispatchEvent(new Event("devolucion:hijo-seleccionado"));
    bootstrap.Modal.getInstance(modalHijos)?.hide();
  }
});

document.addEventListener(
  "input",
  (event) => {
    if (!event.target.matches(".cantidad-recepcion")) return;

    // El campo es texto para evitar los controles nativos, pero conserva
    // cantidades decimales válidas y bloquea letras/símbolos.
    let valor = event.target.value.replace(",", ".").replace(/[^\d.]/g, "");
    const primerPunto = valor.indexOf(".");
    if (primerPunto !== -1) {
      valor = valor.slice(0, primerPunto + 1) + valor.slice(primerPunto + 1).replace(/\./g, "");
    }
    event.target.value = valor;
  },
  true,
);

document.addEventListener("DOMContentLoaded", () => {
  const entradaIdActual = document.getElementById("entrada-id")?.value || "";
  const tipoEntradaActual = document.getElementById("tipo-entrada")?.value || "";
  const claveBorrador = `orvend:recepcion:${tipoEntradaActual}:${entradaIdActual}`;

  const leerBorrador = () => {
    try {
      return JSON.parse(sessionStorage.getItem(claveBorrador)) || {};
    } catch (_) {
      return {};
    }
  };

  const escribirBorrador = (borrador) => {
    try {
      sessionStorage.setItem(claveBorrador, JSON.stringify(borrador));
    } catch (_) {
      // La recepción sigue funcionando aunque el navegador bloquee el almacenamiento.
    }
  };

  const filasProducto = (productoId) =>
    Array.from(document.querySelectorAll(".recepcion-product-row")).filter(
      (fila) => fila.querySelector(".producto-id")?.value === String(productoId),
    );

  const guardarProducto = (fila) => {
    const productoId = fila.querySelector(".producto-id")?.value;
    if (!productoId) return;
    const cantidad = Number(fila.querySelector(".cantidad-recepcion")?.value || 0);
    const borrador = leerBorrador();

    if (cantidad <= 0) {
      delete borrador[productoId];
      escribirBorrador(borrador);
      return;
    }

    borrador[productoId] = {
      ProductoId: Number(productoId),
      Nombre: fila.dataset.productoNombre || "",
      Presentacion: fila.dataset.presentacion || "",
      Sku: fila.dataset.sku || "",
      CantidadComprada: Number(fila.dataset.cantidadSolicitada) || 0,
      CantidadRecibida: cantidad,
      FvencimientoISO: fila.querySelector(".fecha-vencimiento")?.value || null,
    };
    escribirBorrador(borrador);
  };

  const restaurarBorrador = () => {
    const borrador = leerBorrador();
    Object.values(borrador).forEach((producto) => {
      filasProducto(producto.ProductoId).forEach((fila) => {
        const maximo = Number(fila.dataset.cantidadSolicitada) || 0;
        const cantidad = Math.min(Number(producto.CantidadRecibida) || 0, maximo);
        producto.CantidadRecibida = cantidad;
        const input = fila.querySelector(".cantidad-recepcion");
        const fecha = fila.querySelector(".fecha-vencimiento");
        if (input) input.value = cantidad > 0 ? cantidad : "";
        if (fecha && producto.FvencimientoISO) fecha.value = producto.FvencimientoISO;
      });
    });
    escribirBorrador(borrador);
  };

  // =====================================================
  // VALIDAR CANTIDADES
  // =====================================================
  function validarCantidades() {
    const rows = document.querySelectorAll(".recepcion-product-row");

    rows.forEach((row) => {
      const input = row.querySelector(".cantidad-recepcion");
      if (!input) return;

      input.addEventListener("input", function () {
        const cantidadMaxima = Number(row.dataset.cantidadSolicitada) || 0;
        let valorIngresado = parseFloat(this.value);

        if (this.value === "") {
          const productoId = row.querySelector(".producto-id")?.value;
          filasProducto(productoId).forEach((otraFila) => {
            const otroInput = otraFila.querySelector(".cantidad-recepcion");
            if (otroInput && otroInput !== this) otroInput.value = "";
          });
          guardarProducto(row);
          return;
        }

        if (valorIngresado > cantidadMaxima) {
          this.value = cantidadMaxima;
        }

        if (valorIngresado < 0) {
          this.value = 0;
        }

        const productoId = row.querySelector(".producto-id")?.value;
        filasProducto(productoId).forEach((otraFila) => {
          const otroInput = otraFila.querySelector(".cantidad-recepcion");
          if (otroInput && otroInput !== this) otroInput.value = this.value;
        });
        guardarProducto(row);
      });

      row.querySelector(".fecha-vencimiento")?.addEventListener("change", (event) => {
        const productoId = row.querySelector(".producto-id")?.value;
        filasProducto(productoId).forEach((otraFila) => {
          const otraFecha = otraFila.querySelector(".fecha-vencimiento");
          if (otraFecha && otraFecha !== event.target) otraFecha.value = event.target.value;
        });
        guardarProducto(row);
      });
    });
  }

  validarCantidades();
  restaurarBorrador();

  // =====================================================
  // ABRIR MODAL PREVIEW
  // =====================================================
  document
    .getElementById("toggleDropdownPanel32")
    .addEventListener("click", function () {
      const productos = Object.values(leerBorrador())
        .filter((producto) => Number(producto.CantidadRecibida) > 0)
        .map((producto) => {
          let vencimiento = null;
          if (producto.FvencimientoISO) {
            const partes = producto.FvencimientoISO.split("-");
            vencimiento = `${partes[2]}/${partes[1]}/${partes[0]}`;
          }
          return { ...producto, Fvencimiento: vencimiento };
        });

      if (productos.length === 0) {
        Swal.fire({
          icon: "warning",
          title: "Sin productos",
          text: "Debes ingresar cantidades para confirmar.",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }

      const tbodyModal = document.getElementById("tablaDetallesModal");
      const listaModalMovil = document.getElementById("listaConfirmacionModalMovil");
      const mostrarVencimiento = document
        .getElementById("tablacomprar")
        ?.dataset.mostrarVencimiento === "true";
      tbodyModal.innerHTML = "";
      if (listaModalMovil) listaModalMovil.innerHTML = "";

      productos.forEach((p, index) => {
        tbodyModal.innerHTML += `
          <tr class="modal-recepcion-card">
            <td data-label="#">${index + 1}</td>
            <td data-label="Producto ID">${p.ProductoId}</td>
            <td data-label="Producto">${p.Nombre}</td>
            <td data-label="Presentación">${p.Presentacion}</td>
            <td data-label="SKU">${p.Sku}</td>
            <td data-label="Solicitado / recibido">${p.CantidadComprada} / ${p.CantidadRecibida}</td>
            ${mostrarVencimiento ? `<td data-label="Vencimiento">${p.Fvencimiento || "-"}</td>` : ""}
          </tr>
        `;

        if (listaModalMovil) {
          listaModalMovil.insertAdjacentHTML(
            "beforeend",
            `<article class="confirmar-inventario-mobile-card modal-confirmacion-mobile-card">
              <header class="confirmar-inventario-mobile-card__header">
                <span class="confirmar-inventario-mobile-card__icono"><i class="bx bx-package" aria-hidden="true"></i></span>
                <div><small>Producto ${index + 1}</small><strong>${p.Nombre}</strong></div>
                <span class="confirmar-inventario-mobile-card__cantidad">${p.CantidadRecibida}</span>
              </header>
              <div class="confirmar-inventario-mobile-card__datos">
                <div><span><i class="bx bx-box"></i> Presentación</span><strong>${p.Presentacion || "Sin presentación"}</strong></div>
                <div><span><i class="bx bx-list-ol"></i> Solicitada</span><strong>${p.CantidadComprada}</strong></div>
                <div class="confirmar-inventario-mobile-card__sku"><span><i class="bx bx-barcode"></i> SKU</span><strong>${p.Sku || "Sin SKU"}</strong></div>
              </div>
              ${mostrarVencimiento ? `<div class="modal-confirmacion-mobile-card__vencimiento"><i class="bx bx-calendar"></i><span>Vencimiento</span><strong>${p.Fvencimiento || "No indicado"}</strong></div>` : ""}
            </article>`,
          );
        }
      });

      window.productosAutorizacion = productos;

      const modal = new bootstrap.Modal(
        document.getElementById("completarcompra"),
      );
      modal.show();
    });

  // =====================================================
  // ENVIAR AUTORIZACION (COMPRA + TRASLADO)
  // =====================================================
  document
    .getElementById("enviarAutorizacionBtn")
    .addEventListener("click", async () => {
      const entradaIdEl = document.getElementById("entrada-id");
      const tipoEntradaEl = document.getElementById("tipo-entrada");

      const entradaId = entradaIdEl ? entradaIdEl.value : null;

      const tipoEntrada = (tipoEntradaEl?.value || "")
        .toString()
        .trim()
        .toUpperCase();

      const csrfToken = document.querySelector(
        "[name=csrfmiddlewaretoken]",
      ).value;

      // =========================
      // VALIDACIONES
      // =========================
      if (
        !entradaId ||
        !window.productosAutorizacion ||
        window.productosAutorizacion.length === 0
      ) {
        Swal.fire({
          icon: "warning",
          title: "Sin productos",
          text: "Debes seleccionar productos para confirmar.",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }

      if (tipoEntrada !== "COMPRA" && tipoEntrada !== "TRASLADO") {
        Swal.fire({
          icon: "error",
          title: "Tipo inválido",
          text: "El tipo de entrada no es válido (COMPRA / TRASLADO).",
          confirmButtonText: "Aceptar",
        });
        return;
      }

      const payload = {
        EntradaId: parseInt(entradaId),
        TipoEntrada: tipoEntrada,
        Productos: window.productosAutorizacion.map((p) => ({
          ProductoId: p.ProductoId,
          Cantidad: parseFloat(p.CantidadRecibida),
          Fvencimiento: p.Fvencimiento
            ? `${p.Fvencimiento.split("/").reverse().join("-")}T00:00:00`
            : null,
        })),
      };

      console.log("TIPO ENVIADO:", tipoEntrada);
      console.log("PAYLOAD:", payload);

      const modalElement = document.getElementById("completarcompra");
      const modalInstance = bootstrap.Modal.getInstance(modalElement);

      try {
        Swal.fire({
          title: "Procesando...",
          text: "Confirmando entrada de inventario",
          allowOutsideClick: false,
          didOpen: () => Swal.showLoading(),
        });

        const response = await fetch(
          "/manager/bodega/detalleinventario/post/",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify(payload),
          },
        );

        const data = await response.json();
        Swal.close();

        if (data.success) {
          sessionStorage.removeItem(claveBorrador);
          if (modalInstance) modalInstance.hide();

          Swal.fire({
            title: "¡Éxito!",
            text: data.message || "Entrada confirmada correctamente.",
            icon: "success",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          }).then(() => {
            window.location.href = "/manager/bodega/recepcion_inventario/";
          });
        } else {
          Swal.fire({
            title: "Error",
            text: data.message || "No se pudo confirmar.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          });
        }
      } catch (error) {
        console.error(error);
        Swal.close();

        Swal.fire({
          title: "Error",
          text: "Error inesperado de conexión.",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
      }
    });
});
