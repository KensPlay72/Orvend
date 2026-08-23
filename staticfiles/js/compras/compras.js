
//----------------
// ELIMINACION
//----------------
document.addEventListener('DOMContentLoaded', () => {
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

            if (result.isConfirmed){
                try {
                    const response = await fetch(`/manager/compras/delete/${userId}/`, {
                        method: "DELETE",
                        headers: {
                            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Eliminar fila de la tabla sin recargar
                        Swal.fire({
                            title: "Eliminado",
                            text: data.message,
                            icon: "success",
                            confirmButtonText: "Aceptar",
                            customClass: { confirmButton: "classbotones" }
                        }).then(() => {
                            window.location.reload(true);
                        });
                    } else {
                        Swal.fire({
                            title: "Error",
                            text: data.message || "No se pudo eliminar el usuario",
                            icon: "error",
                            confirmButtonText: "Aceptar",
                            customClass: { confirmButton: "classbotones" }
                        });
                    }
                } catch (error) {
                    Swal.fire({
                        title: "Error",
                        text: "Error de conexión o inesperado. Ver consola para más detalles.",
                        icon: "error",
                        confirmButtonText: "Aceptar",
                        customClass: { confirmButton: "classbotones" }
                    });
                console.log(error);
                }
            }
        }
    });
});



document.addEventListener('DOMContentLoaded', function () {
        const filas = document.querySelectorAll('#tablacont tbody tr');

        filas.forEach(fila => {
            fila.addEventListener('click', function (e) {
                if (e.target.closest('button')) return;

                const compraId = this.dataset.id;
                if (compraId) {
                    window.location.href = `/manager/compras/detallecompra/${compraId}`;
                }
            });
        });
    });

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-edit").forEach(btn => {
        btn.addEventListener("click", function () {
            const compraId = this.dataset.id;
            window.location.href = `/manager/compras/edit/${compraId}/`;
        });
    });
});


document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-pdf");
    if (!btn) return;

    const compraId = btn.dataset.id;
    console.log("PDF click compra:", compraId);

    fetch(`/manager/compras/pdf/${compraId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(res => {
        if (!res.ok) throw new Error("Error al generar PDF");
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Compra_${compraId}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    })
    .catch(err => alert(err.message));
});