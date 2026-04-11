//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("postregistro");
    const modalElement = document.getElementById("modalregis");
    const modal = new bootstrap.Modal(modalElement);
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload ={
            Nombre: document.getElementById("ncategoria").value,
            Descripcion: document.getElementById("desccategoria").value,
        }

        try {
            const response = await fetch("/manager/categorias/post/", {
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


//----------------------
// LLENAR FORMULARIO
//----------------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const id = button.getAttribute("data-id");
            const response = await fetch(`/manager/categorias/get/${id}/`);
            const data = await response.json();

            if (data.success){
                const categoria = data.categoria;
                document.getElementById("idedit").value = categoria.id;
                document.getElementById("ncategoriaedit").value = categoria.nombre;
                document.getElementById("desccategoriaedit").value = categoria.descripcion;

                const isActiveCheckbox = document.getElementById("isActiveedit");
                const activeText = document.getElementById("activeTextedit");
                if (categoria.isActive) {
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
        Nombre: document.getElementById("ncategoriaedit").value,
        Descripcion: document.getElementById("desccategoriaedit").value,
    }

    const isActiveCheckbox = document.getElementById("isActiveedit");
    if (!isActiveCheckbox.checked) payload.IsActive = false;

    try {
        const response = await fetch(`/manager/categorias/put/${id}/`, {
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
document.addEventListener("DOMContentLoaded", () => {
    const tabla = document.getElementById("tablacont");

    tabla.addEventListener("click", async (e) => {
        if (e.target.closest(".btn-delete")) {
            const btn = e.target.closest(".btn-delete");
            const id = btn.getAttribute("data-id");
            const nombre = btn.closest("tr").children[1].innerText;

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
                    const response = await fetch(`/manager/categorias/delete/${id}/`, {
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






