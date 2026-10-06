document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".traslados-mobile-card[data-detail-url]").forEach((card) => {
    card.addEventListener("click", (event) => {
      const url = card.dataset.detailUrl;
      if (!url || event.defaultPrevented) return;
      event.preventDefault();
      window.location.assign(url);
    });
  });

  document.querySelectorAll(".fila-traslado[data-token]").forEach((fila) => {
    fila.addEventListener("click", (event) => {
      if (event.target.closest("button, a, input, select, label")) return;
      const token = fila.dataset.token;
      if (token) window.location.href = `/manager/traslados/orden/${token}/`;
    });
  });
});
