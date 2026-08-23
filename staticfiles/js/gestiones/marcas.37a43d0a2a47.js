//----------------
// REGISTRAR
//----------------
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('postregistro');
    const modalElement = document.getElementById('modalregis');
    const modal = new bootstrap.Modal(modalElement);
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        

        const payload ={
            Nombre: document.getElementById('nmarca').value,
            Descripcion: document.getElementById('descmarca').value,
        }
        try{
            const response = await fetch("/manager/marcas/post/", {
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


//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const marcaId = button.getAttribute("data-id");
            const response = await fetch(`/manager/marcas/get/${marcaId}/`);
            const data = await response.json();

            if (data.success) {
                const marca = data.marca;
                document.getElementById("idmarcaid").value = marca.id;
                document.getElementById("nmarcaedit").value = marca.nombre;
                document.getElementById("descmarcaedit").value = marca.descripcion;


                const isActiveCheckbox = document.getElementById("isActiveedit");
                const activeText = document.getElementById("activeTextedit");
                if (marca.isActive) {
                    isActiveCheckbox.checked = true;
                    activeText.textContent = "Activo";
                    activeText.classList.replace("text-danger", "text-success");
                }else{
                    isActiveCheckbox.checked = false;
                    activeText.textContent = "Inactivo";
                    activeText.classList.replace("text-success", "text-danger");
                }
            } else {
                Swal.fire("Error", data.message || "No se pudo obtener la informacion", "error");
            }
        });
    });
});


//----------------
// EDICION
//----------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
    e.preventDefault();

    const idmarcaid = document.getElementById("idmarcaid").value;
    const payload = {
        Nombre: document.getElementById("nmarcaedit").value,
        Descripcion: document.getElementById("descmarcaedit").value,
        IsActive: document.getElementById("isActiveedit").checked,
    };

    try {
        const response = await fetch(`/manager/marcas/put/${idmarcaid}/`, {
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
            }).then(() => {
                window.location.reload(true);
            });
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
                    const response = await fetch(`/manager/marcas/delete/${userId}/`, {
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
                }
            }
        }
    });
});