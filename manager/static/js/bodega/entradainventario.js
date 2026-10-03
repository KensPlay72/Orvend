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

  function validarCantidades() {
    const rows = document.querySelectorAll("#tabladecom tbody tr");

    rows.forEach((row) => {
      const input = row.querySelector(".cantidad-recepcion");
      if (!input) return;

      input.addEventListener("input", function () {
        const cantidadMaxima = parseFloat(row.children[5].innerText) || 0;
        let valorIngresado = parseFloat(this.value);

        if (this.value === "") return;

        if (valorIngresado > cantidadMaxima) {
          this.value = cantidadMaxima;
        }

        if (valorIngresado < 0) {
          this.value = 0;
        }
      });
    });
  }

  validarCantidades();

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
      bootstrap.Modal.getOrCreateInstance(modalHijos).show();
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
  // =====================================================
  // VALIDAR CANTIDADES
  // =====================================================
  function validarCantidades() {
    const rows = document.querySelectorAll("#tabladecom tbody tr");

    rows.forEach((row) => {
      const input = row.querySelector(".cantidad-recepcion");
      if (!input) return;

      input.addEventListener("input", function () {
        const cantidadMaxima = parseFloat(row.children[5].innerText) || 0;
        let valorIngresado = parseFloat(this.value);

        if (this.value === "") return;

        if (valorIngresado > cantidadMaxima) {
          this.value = cantidadMaxima;
        }

        if (valorIngresado < 0) {
          this.value = 0;
        }
      });
    });
  }

  validarCantidades();

  // =====================================================
  // ABRIR MODAL PREVIEW
  // =====================================================
  document
    .getElementById("toggleDropdownPanel32")
    .addEventListener("click", function () {
      const rows = document.querySelectorAll("#tabladecom tbody tr");
      const productos = [];

      rows.forEach((row) => {
        const cantidadInput = row.querySelector(".cantidad-recepcion");

        const cantidadRecibida =
          cantidadInput && cantidadInput.value !== ""
            ? parseFloat(cantidadInput.value)
            : 0;

        if (cantidadRecibida > 0) {
          const productoId = row.querySelector(".producto-id").value;
          const nombre = row.children[1].innerText;
          const presentacion = row.children[3].innerText;
          const sku = row.children[4].innerText;
          const cantidadSolicitada = parseFloat(row.children[5].innerText);

          const fvencimientoInput = row.querySelector(".fecha-vencimiento");
          let fvencimiento = null;

          if (fvencimientoInput && fvencimientoInput.value) {
            const partes = fvencimientoInput.value.split("-");
            fvencimiento = `${partes[2]}/${partes[1]}/${partes[0]}`;
          }

          productos.push({
            ProductoId: parseInt(productoId),
            Nombre: nombre,
            Presentacion: presentacion,
            Sku: sku,
            CantidadComprada: cantidadSolicitada,
            CantidadRecibida: cantidadRecibida,
            Fvencimiento: fvencimiento,
          });
        }
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
      const mostrarVencimiento = document
        .getElementById("tablacomprar")
        ?.dataset.mostrarVencimiento === "true";
      tbodyModal.innerHTML = "";

      productos.forEach((p, index) => {
        tbodyModal.innerHTML += `
          <tr>
            <td>${index + 1}</td>
            <td>${p.ProductoId}</td>
            <td>${p.Nombre}</td>
            <td>${p.Presentacion}</td>
            <td>${p.Sku}</td>
            <td>${p.CantidadComprada} / ${p.CantidadRecibida}</td>
            ${mostrarVencimiento ? `<td>${p.Fvencimiento || "-"}</td>` : ""}
          </tr>
        `;
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
