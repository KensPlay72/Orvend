document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-edit").forEach(btn => {
        btn.addEventListener("click", function () {
            const compraId = this.dataset.id;
            window.location.href = `/manager/bodega/autorizar/${compraId}/`;
        });
    });
});


