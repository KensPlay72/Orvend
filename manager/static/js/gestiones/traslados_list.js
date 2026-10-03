document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".fila-traslado[data-token]").forEach((fila) => {
    fila.addEventListener("click", (event) => {
      if (event.target.closest("button, a, input, select, label")) return;
      const token = fila.dataset.token;
      if (token) window.location.href = `/manager/traslados/orden/${token}/`;
    });
  });
});
