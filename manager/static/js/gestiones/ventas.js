document.addEventListener("DOMContentLoaded", () => {
  const formulario = document.getElementById("ventasFilterForm");
  const boton = document.getElementById("exportarVentasExcel");

  if (!formulario || !boton) return;

  const iconoOriginal = "bx bx-spreadsheet";

  boton.addEventListener("click", async () => {
    const icono = boton.querySelector("i");
    const parametros = new URLSearchParams(new FormData(formulario));

    boton.disabled = true;
    icono.className = "bx bx-loader-alt bx-spin";
    boton.setAttribute("aria-label", "Generando archivo de Excel");

    try {
      const respuesta = await fetch(
        `${formulario.dataset.exportUrl}?${parametros.toString()}`,
      );

      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = "ventas.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch (error) {
      Swal.fire("Error", "No se pudo exportar el reporte de ventas", "error");
    } finally {
      boton.disabled = false;
      icono.className = iconoOriginal;
      boton.setAttribute("aria-label", "Exportar ventas a Excel");
    }
  });
});
