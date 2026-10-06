document.addEventListener("DOMContentLoaded", function () {
  document.addEventListener("click", (event) => {
    const fila = event.target.closest("[data-detail-url]");
    if (!fila || event.target.closest("button, a, input, select, textarea")) return;
    sessionStorage.setItem(
      "orvend:recepcion:return-url",
      `${window.location.pathname}${window.location.search}`,
    );
    window.location.assign(fila.dataset.detailUrl);
  });

  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", function () {
      const token = this.dataset.token;
      const tipo = this.dataset.tipo;

      sessionStorage.setItem(
        "orvend:recepcion:return-url",
        `${window.location.pathname}${window.location.search}`,
      );
      window.location.href = `/manager/bodega/autorizar/${tipo}/${token}/`;
    });
  });

  document.querySelectorAll(".btn-marcar-llegada").forEach((btn) => {
    btn.addEventListener("click", async function () {
      const esTraslado = this.dataset.tipo === "Traslado";
      const confirmacion = await Swal.fire({
        title: esTraslado
          ? "¿Confirmar llegada del traslado?"
          : "¿Marcar compra como en bodega?",
        text: esTraslado
          ? "El traslado quedará disponible para recepción, pero todavía no ingresará al inventario."
          : "La compra quedará disponible para recepción, pero no ingresará inventario todavía.",
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
          title: esTraslado ? "Traslado en bodega" : "Compra en bodega",
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
