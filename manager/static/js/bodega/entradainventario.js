document.addEventListener("DOMContentLoaded", () => {

    // ========= VALIDAR INPUTS DE CANTIDADES =========
    function validarCantidades() {
        const rows = document.querySelectorAll("#tabladecom tbody tr");

        rows.forEach(row => {
            const input = row.querySelector(".cantidad-recepcion");
            if (!input) return;

            input.addEventListener("input", function () {
                const cantidadComprada = parseInt(row.children[5].innerText) || 0;
                let valorIngresado = parseInt(this.value) || 0;

                if (valorIngresado > cantidadComprada) {
                    this.value = cantidadComprada; // no dejar pasar más
                }
            });
        });
    }
    validarCantidades();


    // ========= BOTÓN CONFIRMAR ENTRADA (abre modal) =========
    document.getElementById("toggleDropdownPanel32").addEventListener("click", function () {
        const rows = document.querySelectorAll("#tabladecom tbody tr");
        const productos = [];

        rows.forEach(row => {
            const cantidadRecepcionInput = row.querySelector(".cantidad-recepcion");
            const cantidadRecepcion = cantidadRecepcionInput && cantidadRecepcionInput.value
                ? parseInt(cantidadRecepcionInput.value)
                : 0;

            if (cantidadRecepcion > 0) {
                const productoId = row.querySelector(".producto-id").value;
                const nombre = row.children[1].innerText;
                const presentacion = row.children[3].innerText;
                const sku = row.children[4].innerText;
                const cantidadComprada = parseInt(row.children[5].innerText);

                const fvencimientoInput = row.querySelector(".fecha-vencimiento");
                let fvencimiento = null;

                if (fvencimientoInput && fvencimientoInput.value) {
                    // valor nativo de input[type=date] = yyyy-MM-dd
                    const partes = fvencimientoInput.value.split("-");
                    fvencimiento = `${partes[2]}/${partes[1]}/${partes[0]}`; // dd/MM/yyyy
                }

                productos.push({
                    ProductoId: parseInt(productoId),
                    Nombre: nombre,
                    Presentacion: presentacion,
                    Sku: sku,
                    CantidadComprada: cantidadComprada,
                    CantidadRecibida: cantidadRecepcion,
                    Fvencimiento: fvencimiento
                });
            }
        });

        //Validar que haya productos seleccionados
        if (productos.length === 0) {
            Swal.fire({
                icon: "warning",
                title: "Sin productos",
                text: "Debes ingresar al menos una cantidad para autorizar.",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
            return;
        }

        // Mostrar en modal
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

        // Guardar en variable global para enviar después
        window.productosAutorizacion = productos;

        // Abrir modal
        var modal = new bootstrap.Modal(document.getElementById("completarcompra"));
        modal.show();
    });


    // ========= BOTÓN AUTORIZAR (envía a API) =========
    const btnEnviar = document.getElementById("enviarAutorizacionBtn");
    const modalElement = document.getElementById("completarcompra");
    const modal = new bootstrap.Modal(modalElement);

    btnEnviar.addEventListener("click", async () => {
        const compraId = document.getElementById("compra-id").value;

        if (!compraId || !window.productosAutorizacion || window.productosAutorizacion.length === 0) {
            Swal.fire({
                icon: "warning",
                title: "Sin productos",
                text: "Debes seleccionar al menos un producto para autorizar.",
                confirmButtonText: "Entendido",
                customClass: { confirmButton: "classbotones" }
            });
            return;
        }

        // Payload para la API
        const payload = {
            CompraId: parseInt(compraId),
            Productos: window.productosAutorizacion.map(p => ({
                ProductoId: p.ProductoId,
                Cantidad: p.CantidadRecibida,
                // convertir dd/MM/yyyy → yyyy-MM-dd
                Fvencimiento: p.Fvencimiento
                    ? `${p.Fvencimiento.split("/").reverse().join("-")}T00:00:00`
                    : null
            }))
        };

        try {
            const response = await fetch("/manager/bodega/detalleinventario/post/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.success) {
                modal.hide();
                Swal.fire({
                    title: "¡Éxito!",
                    text: data.message || "Los productos fueron autorizados correctamente.",
                    icon: "success",
                    confirmButtonText: "Aceptar",
                    customClass: { confirmButton: "classbotones" }
                }).then(() => window.location.href = "/manager/bodega/recepcion_inventario/");
            } else {
                Swal.fire({
                    title: "Error",
                    text: data.message || "No se pudo completar la autorización.",
                    icon: "error",
                    confirmButtonText: "Aceptar",
                    customClass: { confirmButton: "classbotones" }
                });
            }

        } catch (error) {
            Swal.fire({
                title: "Error",
                text: "Error de conexión o inesperado. Revisa consola para más detalles.",
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
        }
    });

});



// ========= BOTÓN REGISTRAR DEVOLUCIÓN =========
document.addEventListener("DOMContentLoaded", () => {
  const enviarBtn = document.getElementById("enviarDevolucionBtn");

  document.querySelectorAll(".check-devolucion").forEach((check) => {
    check.addEventListener("change", () => {
      const row = check.closest("tr");
      const select = row.querySelector(".motivo-select");
      select.disabled = !check.checked;
    });
  });

  enviarBtn.addEventListener("click", async () => {
    const compraId = document.getElementById("compra-id").value;
    const observaciones = document.getElementById("observaciones").value.trim();

    const productos = [];
    const filas = document.querySelectorAll("#tablaDevolucion tbody tr");

    filas.forEach((fila) => {
      const check = fila.querySelector(".check-devolucion");
      if (check && check.checked) {
        const productoId = parseInt(fila.querySelector(".producto-id").value);
        const cantidad = parseFloat(
          fila.querySelector("td:nth-child(4)").textContent.trim()
        );
        const motivo = fila.querySelector(".motivo-select").value;

        if (!motivo) return;

        productos.push({
          ProductoId: productoId,
          Cantidad: cantidad,
          Motivo: parseInt(motivo)
        });
      }
    });

    if (productos.length === 0) {
      Swal.fire({
        icon: "warning",
        title: "Faltan datos",
        text: "Debes seleccionar al menos un producto y su motivo de devolución.",
        confirmButtonText: "Entendido",
        customClass: { confirmButton: "classbotones" }
      });
      return;
    }

    const payload = {
      CompraId: parseInt(compraId),
      Observaciones: observaciones || "Sin observaciones",
      Productos: productos
    };

    try {
      const response = await fetch("/manager/bodega/devocompras/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error("Respuesta inválida del servidor");
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Devolucion.pdf";
      document.body.appendChild(a);
      a.click();

      a.remove();
      window.URL.revokeObjectURL(url);

      Swal.fire({
        icon: "success",
        title: "Devolución registrada",
        text: "La devolución se registró y el PDF fue generado correctamente.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" }
      }).then(() => {
        location.reload();
      });

    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "Ocurrió un error al procesar la devolución.",
        confirmButtonText: "Cerrar",
        customClass: { confirmButton: "classbotones" }
      });
    }
  });
});
