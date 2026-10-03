//----------------
// ELIMINACION
//----------------
document.addEventListener("DOMContentLoaded", () => {
  const tabla = document.getElementById("tablacont");

  tabla.addEventListener("click", async (e) => {
    if (e.target.closest(".btn-delete")) {
      const btn = e.target.closest(".btn-delete");
      const userId = btn.getAttribute("data-id");
      const nombre = btn.closest("tr").children[0].textContent;

      const result = await Swal.fire({
        title: `¿Eliminar Compra N°${nombre}?`,
        text: "Esta acción no se puede deshacer",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#6c757d",
        confirmButtonText: "Eliminar",
        cancelButtonText: "Cancelar",
      });

      if (result.isConfirmed) {
        try {
          const response = await fetch(`/manager/compras/delete/${userId}/`, {
            method: "DELETE",
            headers: {
              "X-CSRFToken": document.querySelector(
                "[name=csrfmiddlewaretoken]",
              ).value,
            },
          });

          const data = await response.json();

          if (data.success) {
            // Eliminar fila de la tabla sin recargar
            Swal.fire({
              title: "Eliminado",
              text: data.message,
              icon: "success",
              confirmButtonText: "Aceptar",
              customClass: { confirmButton: "classbotones" },
            }).then(() => {
              window.location.reload(true);
            });
          } else {
            Swal.fire({
              title: "Error",
              text: data.message || "No se pudo eliminar el usuario",
              icon: "error",
              confirmButtonText: "Aceptar",
              customClass: { confirmButton: "classbotones" },
            });
          }
        } catch (error) {
          Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado. Ver consola para más detalles.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
          });
          console.log(error);
        }
      }
    }
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const filas = document.querySelectorAll("#tablacont tbody tr");

  filas.forEach((fila) => {
    fila.addEventListener("click", function (e) {
      if (e.target.closest("button")) return;

      const compraToken = this.dataset.token;
      if (compraToken) {
        window.location.href = `/manager/compras/orden/${compraToken}/`;
      }
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", function () {
      const compraToken = this.dataset.token;
      window.location.href = `/manager/compras/documento/${compraToken}/`;
    });
  });
});

document.addEventListener("click", function (e) {
  const btn = e.target.closest(".btn-pdf");
  if (!btn) return;

  const compraToken = btn.dataset.token;
  console.log("PDF click compra:", compraToken);

  fetch(`/manager/compras/documento/${compraToken}/pdf/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
  })
    .then((res) => {
      if (!res.ok) throw new Error("Error al generar PDF");
      return res.blob();
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Compra.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((err) => alert(err.message));
});

document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("formExportarCompras");
  const boton = document.getElementById("btnGenerarComprasExcel");
  if (!formulario || !boton) return;

  const iconoOriginal = "bx bx-spreadsheet";
  formulario.addEventListener("submit", async (event) => {
    event.preventDefault();
    const parametros = new URLSearchParams(new FormData(formulario));
    const fechaInicio = parametros.get("fecha_inicio");
    const fechaFin = parametros.get("fecha_fin");

    if (!fechaInicio || !fechaFin || fechaInicio > fechaFin) {
      Swal.fire({
        title: "Rango de fechas inválido",
        text: "Selecciona una fecha inicial anterior o igual a la fecha final.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

    const icono = boton.querySelector("i");
    boton.disabled = true;
    icono.className = "bx bx-loader-alt bx-spin";

    try {
      const respuesta = await fetch(
        `${formulario.dataset.exportUrl}?${parametros.toString()}`,
      );
      if (!respuesta.ok) {
        throw new Error((await respuesta.text()) || "No se pudo generar el archivo.");
      }

      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = `compras_${fechaInicio}_${fechaFin}.xlsx`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
      bootstrap.Modal.getInstance(document.getElementById("modalExportarCompras"))?.hide();
    } catch (error) {
      Swal.fire({
        title: "No se pudo exportar",
        text: error.message || "Inténtalo nuevamente.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      boton.disabled = false;
      icono.className = iconoOriginal;
    }
  });
});
