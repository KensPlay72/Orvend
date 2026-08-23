document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-view").forEach(btn => {
        btn.addEventListener("click", function () {
            const devolucionId = this.dataset.id;
            window.location.href = `/manager/compras/devoluciones/detalles/${devolucionId}/`;
        });
    });
});


document.addEventListener("DOMContentLoaded", function () {

    const id = window.location.pathname.split("/").filter(Boolean).pop();

    // ====================================
    // APROBAR DEVOLUCIÓN
    // ====================================
    const btnAprobar = document.getElementById("btnAprobar");

    if (btnAprobar) {
        btnAprobar.addEventListener("click", function () {

            Swal.fire({
                title: "¿Aprobar devolución?",
                text: "Se marcará como aprobada y se generará el documento PDF.",
                icon: "question",
                showCancelButton: true,
                confirmButtonText: "Sí, aprobar",
                cancelButtonText: "Cancelar",
                confirmButtonColor: "#28a745",
                cancelButtonColor: "#6c757d"
            }).then(async (result) => {

                if (!result.isConfirmed) return;

                try {
                    const res = await fetch(`/manager/compras/devoluciones/aprobar/${id}/`, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": getCookie("csrftoken")
                        }
                    });

                    if (!res.ok) throw new Error("Error al aprobar");

                    const blob = await res.blob();

                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `Devolucion_Aprobada_${id}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();

                    Swal.fire({
                        title: "Devolución aprobada",
                        text: "El documento fue generado correctamente.",
                        icon: "success",
                        confirmButtonText: "Aceptar",
                        customClass: {
                            confirmButton: "classbotones"
                        }
                    }).then(() => {
                        window.location.href = "/manager/compras/devoluciones/";
                    });

                } catch (error) {
                    console.error(error);

                    Swal.fire({
                        title: "Error",
                        text: "No se pudo aprobar la devolución.",
                        icon: "error",
                        confirmButtonText: "Aceptar",
                        customClass: {
                            confirmButton: "classbotones"
                        }
                    });
                }
            });
        });
    }

    // ====================================
    // RECHAZAR DEVOLUCIÓN
    // ====================================
    const btnRechazar = document.getElementById("btnRechazar");

    if (btnRechazar) {
        btnRechazar.addEventListener("click", function () {

            Swal.fire({
                title: "¿Rechazar devolución?",
                text: "Se solicitará un motivo de rechazo.",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Sí, rechazar",
                cancelButtonText: "Cancelar",
                confirmButtonColor: "#dc3545",
                cancelButtonColor: "#6c757d"
            }).then(async (result) => {

                if (!result.isConfirmed) return;

                const { value: motivo } = await Swal.fire({
                    title: "Motivo del rechazo",
                    input: "textarea",
                    inputPlaceholder: "Escribe el motivo...",
                    showCancelButton: true,
                    confirmButtonText: "Aceptar",
                    cancelButtonText: "Cancelar",
                    customClass: {
                        confirmButton: "classbotones",
                        cancelButton: "classbotones"
                    }
                });

                if (!motivo) return;

                try {
                    const res = await fetch(`/manager/compras/devoluciones/rechazar/${id}/`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken")
                        },
                        body: JSON.stringify({ motivo })
                    });

                    if (!res.ok) throw new Error("Error al rechazar");

                    const blob = await res.blob();

                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `Devolucion_Rechazada_${id}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();

                    Swal.fire({
                        title: "Devolución rechazada",
                        text: "El documento fue generado correctamente.",
                        icon: "success",
                        confirmButtonText: "Aceptar",
                        customClass: {
                            confirmButton: "classbotones"
                        }
                    }).then(() => {
                        window.location.href = "/manager/compras/devoluciones/";
                    });

                } catch (error) {
                    console.error(error);

                    Swal.fire({
                        title: "Error",
                        text: "No se pudo rechazar la devolución.",
                        icon: "error",
                        confirmButtonText: "Aceptar",
                        customClass: {
                            confirmButton: "classbotones"
                        }
                    });
                }
            });
        });
    }

});

// ====================================
// CSRF TOKEN
// ====================================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();

            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}