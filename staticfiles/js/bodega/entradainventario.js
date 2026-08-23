document.addEventListener("DOMContentLoaded", () => {
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
        const cantidadRecepcionInput = row.querySelector(".cantidad-recepcion");
        const cantidadRecepcion =
          cantidadRecepcionInput && cantidadRecepcionInput.value !== ""
            ? parseFloat(cantidadRecepcionInput.value)
            : 0;

        if (cantidadRecepcion > 0) {
          const productoId = row.querySelector(".producto-id").value;
          const nombre = row.children[1].innerText;
          const presentacion = row.children[3].innerText;
          const sku = row.children[4].innerText;
          const cantidadComprada = parseFloat(row.children[5].innerText);

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
            CantidadComprada: cantidadComprada,
            CantidadRecibida: cantidadRecepcion,
            Fvencimiento: fvencimiento,
          });
        }
      });

      if (productos.length === 0) {
        Swal.fire({
          icon: "warning",
          title: "Sin productos",
          text: "Debes ingresar al menos una cantidad para autorizar.",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }

      const tbodyModal = document.getElementById("tablaDetallesModal");
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
            <td>${p.Fvencimiento || "-"}</td>
        </tr>
      `;
      });

      window.productosAutorizacion = productos;

      const modal = new bootstrap.Modal(
        document.getElementById("completarcompra"),
      );
      modal.show();
    });
});

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
            <td>${p.Fvencimiento || "-"}</td>
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
