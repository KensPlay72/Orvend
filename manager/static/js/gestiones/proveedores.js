//----------------
// VALIDAR NUMERO EN INPUT
//----------------
function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, '');
}

//----------------
// REGISTRAR
//----------------
document.getElementById("postregistro").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = document.getElementById("postregistro");
    const modalElement = document.getElementById("modalregis");
    const modal = new bootstrap.Modal(modalElement);

    const requiredFields = [
        { id: 'nlegal', name: 'Nombre Legal' },
        { id: 'ncomercial', name: 'Nombre Comercial' },
        { id: 'rtn', name: 'RTN' },
        { id: 'dcreditos', name: 'Días de Crédito' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);
            input.classList.add('input-error');
            if (label) label.classList.add('text-error');
        }
    });

    if (missingFields.length > 0) {
        Swal.fire({
            title: 'Campos incompletos',
            text: 'Por favor completa los siguientes campos: ' + missingFields.join(', '),
            icon: 'warning',
            confirmButtonText: 'Aceptar',
            customClass: { confirmButton: 'classbotones' }
        });
        return;
    }

    const payload = {
        nombre_legal: document.getElementById("nlegal").value.trim(),
        nombre_comercial: document.getElementById("ncomercial").value.trim(),
        rtn: document.getElementById("rtn").value.trim(),
        dias_credito: document.getElementById("dcreditos").value.trim(),
        telefono: document.getElementById("telefono").value.trim(),
        email: document.getElementById("email").value.trim()
    };

    try {
        const response = await fetch("/manager/proveedores/post/", {
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
            form.reset();
            Swal.fire({
                title: "¡Éxito!",
                text: data.message,
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            }).then(() => window.location.reload());
        } else {
            Swal.fire({
                title: "Error",
                text: data.message,
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
        }
    } catch (error) {
        console.error(error);
        Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado. Ver consola para más detalles.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" }
        });
    }
});

//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const proveedorId = button.getAttribute("data-id");
            const response = await fetch(`/manager/proveedores/get/${proveedorId}/`);
            const data = await response.json();
            
            if (data.success) {
                const proveedor = data.proveedor;

                // Llenar campos básicos
                document.getElementById("idproveedor").value = proveedor.id;
                document.getElementById("nlegaledit").value = proveedor.nombre_legal || '';
                document.getElementById("ncomercialedit").value = proveedor.nombre_comercial || '';
                document.getElementById("rtnedit").value = proveedor.rtn || '';
                document.getElementById("dcreditosedit").value = proveedor.dias_credito ?? '';
                document.getElementById("emailedit").value = proveedor.email || '';

                // Teléfono completo
                if (proveedor.telefono) {
                    document.getElementById("telefonoedit").value = proveedor.telefono;
                } else {
                    document.getElementById("telefonoedit").value = '';
                }

                // Estado
                const activeCheckbox = document.getElementById("isActiveedit");
                const activeText = document.getElementById("activeTextedit");

                if (proveedor.is_active) {
                    activeCheckbox.checked = true;
                    activeText.textContent = "Activo";
                    activeText.classList.remove("text-danger");
                    activeText.classList.add("text-success");
                } else {
                    activeCheckbox.checked = false;
                    activeText.textContent = "Inactivo";
                    activeText.classList.remove("text-success");
                    activeText.classList.add("text-danger");
                }
            } else {
                Swal.fire("Error", data.message || "No se pudo obtener la información", "error");
            }
        });
    });
});


//----------------
// EDICION
//----------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
    e.preventDefault();

    const requiredFields = [
        { id: 'nlegaledit', name: 'Nombre Legal' },
        { id: 'ncomercialedit', name: 'Nombre Comercial' },
        { id: 'rtnedit', name: 'RTN' },
        { id: 'dcreditosedit', name: 'Días de Crédito' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);
            input.classList.add('input-error');
            if (label) label.classList.add('text-error');
        }
    });

    if (missingFields.length > 0) {
        Swal.fire({
            title: 'Campos incompletos',
            text: 'Por favor completa los siguientes campos: ' + missingFields.join(', '),
            icon: 'warning',
            confirmButtonText: 'Aceptar',
            customClass: { confirmButton: 'classbotones' }
        });
        return;
    }

    const idproveedor = document.getElementById("idproveedor").value;
    const payload = {
        nombre_legal: document.getElementById("nlegaledit").value.trim(),
        nombre_comercial: document.getElementById("ncomercialedit").value.trim(),
        rtn: document.getElementById("rtnedit").value.trim(),
        dias_credito: document.getElementById("dcreditosedit").value.trim(),
        telefono: document.getElementById("telefonoedit").value.trim(),
        email: document.getElementById("emailedit").value.trim(),
        IsActive: document.getElementById("isActiveedit").checked
    };

    try {
        const response = await fetch(`/manager/proveedores/put/${idproveedor}/`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            Swal.fire({
                title: "¡Éxito!",
                text: data.message || "actualizado correctamente",
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            }).then(() => window.location.reload(true));
        } else {
            Swal.fire({
                title: "Error",
                text: data.message || "Ocurrió un error al actualizar",
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
        }
    } catch (error) {
        console.error(error);
        Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado. Ver consola para más detalles.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" }
        });
    }
});


//----------------
// ELIMINACION
//----------------
document.addEventListener('DOMContentLoaded', () => {
    const tabla = document.getElementById("tablacont");

    tabla.addEventListener("click", async (e) => {
        if (e.target.closest(".btn-delete")) {
            const btn = e.target.closest(".btn-delete");
            const userId = btn.getAttribute("data-id");
            const nombre = btn.closest("tr").children[1].textContent;
            
            const result = await Swal.fire({
                title: `¿Eliminar la marca "${nombre}"?`,
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
                    const response = await fetch(`/manager/proveedores/delete/${userId}/`, {
                        method: "DELETE",
                        headers: {
                            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    });

                    const data = await response.json();

                    if (data.success) {
                        Swal.fire({
                            title: "Eliminado",
                            text: data.message,
                            icon: "success",
                            confirmButtonText: "Aceptar",
                            customClass: { confirmButton: "classbotones" }
                        }).then(() => window.location.reload(true));
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
                    console.error(error);
                    Swal.fire({
                        title: "Error",
                        text: "Error de conexión o inesperado. Ver consola para más detalles.",
                        icon: "error",
                        confirmButtonText: "Aceptar",
                        customClass: { confirmButton: "classbotones" }
                    });
                }
            }
        }
    });
});

// Código de país eliminado: ahora se usa únicamente el input de teléfono
