function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, '');
}


document.addEventListener("DOMContentLoaded", () => {
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