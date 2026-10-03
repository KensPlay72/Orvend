function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, '');
}


document.addEventListener("DOMContentLoaded", () => {
    const modalHistorialElement = document.getElementById("modalHistorialPagar");
    const historialBody = document.getElementById("historialPagarBody");
    const historialCuenta = document.getElementById("historialPagarCuenta");

    if (modalHistorialElement && historialBody && historialCuenta) {
        const tablaCuentas = document.getElementById("tablaUsuarios");
        const escaparHtml = (valor) => String(valor).replace(/[&<>"']/g, (caracter) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
        }[caracter]));
        tablaCuentas?.addEventListener("click", async (event) => {
            if (event.target.closest("button, a, input, select, label")) return;

            const fila = event.target.closest(".fila-cuenta[data-abonos-url]");
            if (!fila) return;

            historialCuenta.textContent = `Cuenta por pagar #${fila.dataset.id}`;
            historialBody.innerHTML = '<tr><td colspan="3" class="text-center">Cargando abonos...</td></tr>';
            bootstrap.Modal.getOrCreateInstance(modalHistorialElement).show();

            try {
                const response = await fetch(fila.dataset.abonosUrl);
                const data = await response.json();
                if (!response.ok || !data.success) throw new Error(data.message || "No se pudo obtener el historial");

                historialBody.innerHTML = data.abonos.length
                    ? data.abonos.map((abono) => `<tr><td>${escaparHtml(abono.usuario)}</td><td>${escaparHtml(abono.fecha)}</td><td>L. ${escaparHtml(abono.monto)}</td></tr>`).join("")
                    : '<tr><td colspan="3" class="text-center table-empty-state">No hay abonos registrados.</td></tr>';
            } catch (error) {
                historialBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">${escaparHtml(error.message)}</td></tr>`;
            }
        });
    }

    const modalElement = document.getElementById("modalregis");
    const abonoInput = document.getElementById("abono");
    const mpagarInput = document.getElementById("mpagar");

    let cuentaId = null;

    // Capturar id y monto al abrir el modal
    modalElement.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;
        const montoapagar = button.getAttribute("data-monto");
        cuentaId = button.getAttribute("data-id");

        mpagarInput.value = montoapagar;
        abonoInput.value = "";
        abonoInput.setAttribute("max", montoapagar);
    });

    // Validar que no supere el monto y solo números/decimales
    abonoInput.addEventListener("input", () => {
        let abono = parseFloat(abonoInput.value) || 0;
        let max = parseFloat(abonoInput.getAttribute("max")) || 0;

        if (abono > max) {
            abonoInput.value = max;
        } else {
            abonoInput.value = abonoInput.value.replace(/[^0-9.]/g, '');
        }
    });

    // Exponer cuentaId para el post
    window.getCuentaId = () => cuentaId;
});

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("postregistro");
    const modalElement = document.getElementById("modalregis");
    const modal = new bootstrap.Modal(modalElement);
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const cuentaId = window.getCuentaId(); 
        const payload = {
            montoAbono: document.getElementById("abono").value,
        }
        try {
            const response = await fetch(`/manager/cppagar/post/${cuentaId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            
            if (data.success) {
                modal.hide();
                Swal.fire({
                    title: "¡Éxito!",
                    text: data.message || "registrado correctamente",
                    icon: "success",
                    confirmButtonText: "Aceptar",
                    customClass: { confirmButton: "classbotones" }
                }).then(() => { 
                    window.location.reload(true); 
                });
            } else {
                Swal.fire({
                    title: "Error",
                    text: data.message || "Ocurrió un error al registrar",
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
        }
    });
});
