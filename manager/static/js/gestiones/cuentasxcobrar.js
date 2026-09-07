window.validateNumber = function (input) {
    input.value = input.value.replace(/[^0-9.]/g, "");
};

document.addEventListener("DOMContentLoaded", () => {
    const modalElement = document.getElementById("modalAbonoCobrar");
    const form = document.getElementById("formAbonoCobrar");
    const montoPendiente = document.getElementById("montoPendienteCobrar");
    const abono = document.getElementById("abonoCobrar");

    if (!modalElement || !form || !montoPendiente || !abono) {
        return;
    }

    const modal = new bootstrap.Modal(modalElement);
    let cuentaId = null;

    modalElement.addEventListener("show.bs.modal", (event) => {
        const boton = event.relatedTarget;
        cuentaId = boton?.dataset.id || null;
        const pendiente = boton?.dataset.monto || "0";

        montoPendiente.value = pendiente;
        abono.value = "";
        abono.max = pendiente;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (!cuentaId) {
            return;
        }

        try {
            const response = await fetch(`/manager/cxcobrar/post/${cuentaId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
                },
                body: JSON.stringify({ montoAbono: abono.value }),
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "No se pudo registrar el abono");
            }

            modal.hide();
            Swal.fire({
                title: "¡Éxito!",
                text: data.message,
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" },
            }).then(() => window.location.reload());
        } catch (error) {
            Swal.fire({
                title: "Error",
                text: error.message,
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" },
            });
        }
    });
});
