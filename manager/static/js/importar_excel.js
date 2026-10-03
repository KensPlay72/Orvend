document.querySelectorAll(".excel-import-form").forEach((formulario) => {
  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const boton = formulario.querySelector('button[type="submit"]');
    const contenidoOriginal = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Importando';
    try {
      const respuesta = await fetch(formulario.dataset.importUrl, {
        method: "POST",
        headers: { "X-CSRFToken": formulario.querySelector('[name="csrfmiddlewaretoken"]').value },
        body: new FormData(formulario),
      });
      const data = await respuesta.json();
      if (!respuesta.ok || !data.success) throw new Error(data.message || "No se pudo importar el archivo.");
      bootstrap.Modal.getOrCreateInstance(formulario.closest(".modal")).hide();
      Swal.fire({ title: "Importación completada", text: data.message, icon: "success", confirmButtonText: "Aceptar", customClass: { confirmButton: "classbotones" } }).then(() => window.location.reload());
    } catch (error) {
      Swal.fire({ title: "No se pudo importar", text: error.message, icon: "error", confirmButtonText: "Aceptar", customClass: { confirmButton: "classbotones" } });
    } finally {
      boton.disabled = false;
      boton.innerHTML = contenidoOriginal;
    }
  });
});
