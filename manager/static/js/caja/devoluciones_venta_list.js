document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("devolucionesFilterForm");
  const boton = document.getElementById("exportarDevolucionesExcel");
  if (!formulario || !boton) return;

  boton.addEventListener("click", async () => {
    const icono = boton.querySelector("i");
    const claseOriginal = icono.className;
    const parametros = new URLSearchParams(new FormData(formulario));
    boton.disabled = true;
    icono.className = "bx bx-loader-alt bx-spin";

    try {
      const respuesta = await fetch(
        `${formulario.dataset.exportUrl}?${parametros}`,
      );
      if (!respuesta.ok) throw new Error();
      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = "devoluciones_venta.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch {
      Swal.fire({
        title: "Error",
        text: "No se pudo exportar el reporte de devoluciones",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      boton.disabled = false;
      icono.className = claseOriginal;
    }
  });
});
