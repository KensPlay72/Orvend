document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("tr[data-detail-url]").forEach((fila) => {
    fila.addEventListener("click", (event) => {
      if (event.target.closest("button, a, input, select, textarea")) return;
      window.location.href = fila.dataset.detailUrl;
    });
  });

  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", function () {
      const token = this.dataset.token;
      const tipo = this.dataset.tipo;

      window.location.href = `/manager/bodega/autorizar/${tipo}/${token}/`;
    });
  });

  document.querySelectorAll(".btn-marcar-llegada").forEach((btn) => {
    btn.addEventListener("click", async function () {
      const confirmacion = await Swal.fire({
        title: "¿Registrar llegada a bodega?",
        text: "La compra quedará disponible para recepción, pero no ingresará inventario todavía.",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Sí, registrar llegada",
        cancelButtonText: "Cancelar",
        reverseButtons: true,
        customClass: { confirmButton: "classbotones" },
      });
      if (!confirmacion.isConfirmed) return;

      const csrfToken = document.querySelector(
        '[name="csrfmiddlewaretoken"]',
      )?.value;
      try {
        const response = await fetch(this.dataset.url, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken },
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.mensaje || "No se pudo registrar la llegada.");
        }
        await Swal.fire({
          title: "Llegada registrada",
          text: data.mensaje,
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        window.location.reload();
      } catch (error) {
        Swal.fire({
          title: "No se pudo registrar",
          text: error.message || "Inténtalo nuevamente.",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
      }
    });
  });
});
