//----------------
// REGISTRAR
//----------------
document.addEventListener('DOMContentLoaded', function () {

    const form = document.getElementById("postregistro");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const nombre = document.getElementById("npresentacion").value.trim();
        const abreviatura = document.getElementById("abreviatura").value.trim();

        if (!nombre || !abreviatura) {
            Swal.fire({
                title: "Error",
                text: "Nombre y abreviatura son obligatorios",
                icon: "error"
            });
            return;
        }

        const payload = {
            nombre,
            abreviatura,
        };

        try {
            const response = await fetch("/manager/presentaciones/post/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok && data.success) {

                const modalEl = document.getElementById("modalregis");
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                modalInstance.hide();

                form.reset();

                Swal.fire({
                    title: "¡Éxito!",
                    text: data.message || "Registrado correctamente",
                    icon: "success",
                    confirmButtonText: "Aceptar",
                    customClass: { confirmButton: "classbotones" }
                }).then(() => {
                    window.location.reload();
                });

            } else {

                Swal.fire({
                    title: "Error",
                    text: data.message || "Ocurrió un error",
                    icon: "error",
                    confirmButtonText: "Aceptar",
                    customClass: { confirmButton: "classbotones" }
                });
            }

        } catch (error) {
            console.error(error);

            Swal.fire({
                title: "Error",
                text: "Error de conexión o servidor",
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
        }
    });
});

//----------------------
// LLENAR FORMULARIO
//----------------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const id = button.getAttribute("data-id");
            const response = await fetch(`/manager/presentaciones/get/${id}/`);
            const data = await response.json();

            if (data.success){
                const presentacion = data.presentacion;
                document.getElementById("idedit").value = presentacion.id;
                document.getElementById("npresentacionedit").value = presentacion.nombre;
                document.getElementById("abreviaturaedit").value = presentacion.abreviatura;

                const isActiveCheckbox = document.getElementById("isActiveedit");
                const activeText = document.getElementById("activeTextedit");
                if (presentacion.isActive) {
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


//----------------------
// EDICION
//----------------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("idedit").value;

    const payload ={
        Nombre: document.getElementById("npresentacionedit").value,
        Abreviatura: document.getElementById("abreviaturaedit").value,
    }

    const isActiveCheckbox = document.getElementById("isActiveedit");
    if (!isActiveCheckbox.checked) payload.IsActive = false;

    try {
        const response = await fetch(`/manager/presentaciones/put/${id}/`, {
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
                text: data.message || "Actualizado correctamente",
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
document.addEventListener("DOMContentLoaded", () => {
    const tabla = document.getElementById("tablacont");

    tabla.addEventListener("click", async (e) => {
        if (e.target.closest(".btn-delete")) {
            const btn = e.target.closest(".btn-delete");
            const id = btn.getAttribute("data-id");
            const nombre = btn.closest("tr").children[1].innerText;

            const result = await Swal.fire({
                title: `¿Eliminar la presentación "${nombre}"?`,
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
                    const response = await fetch(`/manager/presentaciones/delete/${id}/`, {
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