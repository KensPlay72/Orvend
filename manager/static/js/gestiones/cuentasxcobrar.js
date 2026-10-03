window.validateNumber = function (input) {
    input.value = input.value.replace(/[^0-9.]/g, "");
};

document.addEventListener("DOMContentLoaded", () => {
    const modalHistorialElement = document.getElementById("modalHistorialCobrar");
    const historialBody = document.getElementById("historialCobrarBody");
    const historialCuenta = document.getElementById("historialCobrarCuenta");

    if (modalHistorialElement && historialBody && historialCuenta) {
        const modalHistorial = new bootstrap.Modal(modalHistorialElement);
        const escaparHtml = (valor) => String(valor).replace(/[&<>"']/g, (caracter) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
        }[caracter]));
        document.querySelectorAll(".fila-cuenta[data-abonos-url]").forEach((fila) => {
            fila.addEventListener("click", async (event) => {
                if (event.target.closest("button, a, input, select, label")) return;

                historialCuenta.textContent = `Cuenta por cobrar #${fila.dataset.id}`;
                historialBody.innerHTML = '<tr><td colspan="3" class="text-center">Cargando abonos...</td></tr>';
                modalHistorial.show();

                try {
                    const response = await fetch(fila.dataset.abonosUrl);
                    const data = await response.json();
                    if (!response.ok || !data.success) throw new Error(data.message || "No se pudo obtener el historial");

                    historialBody.innerHTML = data.abonos.length
                        ? data.abonos.map((abono) => `<tr><td>${escaparHtml(abono.usuario)}</td><td>${escaparHtml(abono.fecha)}</td><td>L. ${escaparHtml(abono.monto)}</td></tr>`).join("")
                        : '<tr><td colspan="3" class="text-center table-empty-state">No hay abonos registrados.</td></tr>';
                } catch (error) {
                    historialBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">${error.message}</td></tr>`;
                }
            });
        });
    }

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
