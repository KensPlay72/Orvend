document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", function () {
      const id = this.dataset.id;
      const tipo = this.dataset.tipo;

      window.location.href = `/manager/bodega/autorizar/${tipo}/${id}/`;
    });
  });
});
