//----------------
// REGISTRAR 
//----------------
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('postregistro');
    const modalElement = document.getElementById('modalregis');
    const modal = new bootstrap.Modal(modalElement);

    // Función para convertir imagen a WebP
    function convertImageToWebP(file, quality = 0.8) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(event) {
                const img = new Image();
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    canvas.toBlob(
                        (blob) => {
                            if (blob) {
                                const webpFile = new File([blob], file.name.replace(/\.[^/.]+$/, ".webp"), { type: "image/webp" });
                                resolve(webpFile);
                            } else {
                                reject(new Error('No se pudo convertir la imagen a WebP'));
                            }
                        },
                        'image/webp',
                        quality
                    );
                };
                img.onerror = reject;
                img.src = event.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

    const requiredFields = [
        { id: 'Nombre', name: 'Nombre' },
        { id: 'Descripcion', name: 'Descripción' },
        { id: 'CategoriaId', name: 'Categoría' },
        { id: 'UnidadMedidaId', name: 'Presentación' },
        { id: 'MarcaId', name: 'Marca' },
        { id: 'CodigoSKU', name: 'Código SKU' },
        { id: 'precioVenta', name: 'Precio de Venta' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        // Limpiar errores anteriores
        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);

            // Si es input hidden (como CategoriaId), marcar el botón del dropdown
            if (input.type === "hidden") {
                const dropdownButton = formGroup.querySelector('.dropdown .btn');
                if (dropdownButton) dropdownButton.classList.add('input-error');
                if (label) label.classList.add('text-error');
            } else {
                input.classList.add('input-error');
                if (label) label.classList.add('text-error');
            }
        } else {
            // Limpiar estilos en caso de que haya sido corregido
            if (input.type === "hidden") {
                const dropdownButton = formGroup.querySelector('.dropdown .btn');
                if (dropdownButton) dropdownButton.classList.remove('input-error');
                if (label) label.classList.remove('text-error');
            }
        }
    });

    // Mostrar alerta si hay campos faltantes
    if (missingFields.length > 0) {
        Swal.fire({
            title: 'Campos incompletos',
            text: 'Por favor completa los siguientes campos: ' + missingFields.join(', '),
            icon: 'warning',
            confirmButtonText: 'Aceptar',
            customClass: {
                confirmButton: 'classbotones'
            }
        });
        return; // Evitar envío del formulario
    }


        // Construir FormData con campos
        const formData = new FormData();
        formData.append("nombre", document.getElementById('Nombre').value);
        formData.append("descripcion", document.getElementById('Descripcion').value);
        formData.append("categoria", document.getElementById('CategoriaId').value);
        formData.append("unidad_medida", document.getElementById('UnidadMedidaId').value);
        formData.append("marca", document.getElementById('MarcaId').value);
        formData.append("codigo_sku", document.getElementById('CodigoSKU').value);
        formData.append("precio_venta", document.getElementById('precioVenta').value);

        const vencimientoCheckbox = document.getElementById("vencimiento");
        formData.append("Vencimiento", vencimientoCheckbox.checked);

        const imagenInput = document.getElementById("imagenproducto");

        if (imagenInput.files && imagenInput.files[0]) {
            const file = imagenInput.files[0];
            const fileExtension = file.name.split('.').pop().toLowerCase();

            if (fileExtension !== "jpg" && fileExtension !== "png" && fileExtension !== "jpeg" && fileExtension !== "webp") {
                Swal.fire({
                    title: 'Archivo no válido',
                    text: 'Por favor, sube una imagen en formato JPG o PNG.',
                    icon: 'error',
                    confirmButtonText: 'Aceptar',
                    customClass: { confirmButton: 'custom-alertas-button' }
                });
                return; // Detener submit si formato inválido
            }

            try {
                // Convertimos la imagen a WebP antes de enviarla
                const webpFile = await convertImageToWebP(file);
                formData.append("Imagen", webpFile);
            } catch (error) {
                Swal.fire({
                    title: 'Error',
                    text: 'No se pudo procesar la imagen.',
                    icon: 'error',
                    confirmButtonText: 'Aceptar',
                    customClass: { confirmButton: 'custom-alertas-button' }
                });
                return; // Detener submit si falla la conversión
            }
        }

        try {
            const response = await fetch("/manager/productos/post/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: formData
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
                }).then(() => {
                    window.location.reload();
                });
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
            Swal.fire({
                title: "Error",
                text: "Error de conexión o inesperado. Ver consola para más detalles.",
                icon: "error",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
            console.error(error);
        }
    });
});

        
//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const Id = button.getAttribute("data-id");
            const response = await fetch(`/manager/productos/get/${Id}/`);
            const data = await response.json();

            if (!data.success) {
                Swal.fire("Error", data.message || "No se pudo obtener la información", "error");
                return;
            }

            const producto = data.producto;

            /* =========================
               CAMPOS BÁSICOS
            ========================= */
            document.getElementById("idedit").value = producto.id;
            document.getElementById("Nombreedit").value = producto.nombre;
            document.getElementById("Descripcionedit").value = producto.descripcion;
            document.getElementById("CodigoSKUedit").value = producto.codigoSKU;
            document.getElementById("precioVentaedit").value = producto.precioVenta;

            document.getElementById("ImagenNombreActual").value = producto.imagenNombre;
            document.getElementById("ImagenUrlActual").value = producto.imagenUrl;

            document.getElementById("imagenNombreedit").textContent =
                producto.imagenNombre || "No hay imagen cargada";

            /* =========================
               CATEGORÍA (REMOTE)
            ========================= */
            setRemoteSelectEdit({
                hiddenId: "CategoriaIdedit",
                value: producto.categoriaId,
                text: producto.categoria?.nombre,
                placeholder: "Categoría"
            });

            /* =========================
               PRESENTACIÓN / U MEDIDA
            ========================= */
            setRemoteSelectEdit({
                hiddenId: "UnidadMedidaIdedit",
                value: producto.unidadMedidaId,
                text: producto.unidadMedida
                    ? `${producto.unidadMedida.nombre} | ${producto.unidadMedida.abreviatura}`
                    : "",
                placeholder: "Presentación"
            });

            /* =========================
               MARCA (REMOTE)
            ========================= */
            setRemoteSelectEdit({
                hiddenId: "MarcaIdedit",
                value: producto.marcasId,
                text: producto.marcas?.nombre,
                placeholder: "Marca"
            });

            /* =========================
               ESTADO
            ========================= */
            const activeCheckbox = document.getElementById("isActiveedit");
            const activeText = document.getElementById("activeTextedit");

            activeCheckbox.checked = producto.isActive;
            activeText.textContent = producto.isActive ? "Activo" : "Inactivo";
            activeText.classList.toggle("text-success", producto.isActive);
            activeText.classList.toggle("text-danger", !producto.isActive);

            /* =========================
               VENCIMIENTO
            ========================= */
            const vencimientoCheckbox = document.getElementById("vencimientoedit");
            const vencimientoText = document.getElementById("vencimientoTextedit");

            vencimientoCheckbox.checked = producto.vencimiento;
            vencimientoText.textContent = producto.vencimiento ? "SI" : "NO";
            vencimientoText.classList.toggle("text-success", producto.vencimiento);
            vencimientoText.classList.toggle("text-danger", !producto.vencimiento);
        });
    });
});


function setRemoteSelectEdit({ hiddenId, value, text, placeholder }) {
    const hiddenInput = document.getElementById(hiddenId);
    const dropdownBtn = document.querySelector(`#${hiddenId} ~ .select-container button`);
    const optionsContainer = document.querySelector(`#${hiddenId} ~ .select-container .options`);

    hiddenInput.value = value || "";
    dropdownBtn.textContent = text || placeholder;

    optionsContainer.innerHTML = "";

    if (value && text) {
        optionsContainer.innerHTML = `
            <button type="button"
                    class="list-group-item list-group-item-action"
                    data-value="${value}">
                ${text}
            </button>
        `;
    }
}


//----------------------
// EDICION
//----------------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
    e.preventDefault();
    const Id = document.getElementById("idedit").value;

    // Validación de campos requeridos
    const requiredFields = [
        { id: 'Nombreedit', name: 'Nombre' },
        { id: 'Descripcionedit', name: 'Descripción' },
        { id: 'CategoriaIdedit', name: 'Categoría' },
        { id: 'UnidadMedidaIdedit', name: 'Presentación' },
        { id: 'MarcaIdedit', name: 'Marca' },
        { id: 'CodigoSKUedit', name: 'Código de Barras' },
        { id: 'precioVentaedit', name: 'Precio de Venta' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        // Limpiar errores anteriores
        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);

            // Si es input hidden, marcar el botón visible del dropdown
            if (input.type === "hidden") {
                const dropdownButton = formGroup.querySelector('.dropdown .btn');
                if (dropdownButton) dropdownButton.classList.add('input-error');
                if (label) label.classList.add('text-error');
            } else {
                input.classList.add('input-error');
                if (label) label.classList.add('text-error');
            }
        } else {
            // Limpiar si fue corregido
            if (input.type === "hidden") {
                const dropdownButton = formGroup.querySelector('.dropdown .btn');
                if (dropdownButton) dropdownButton.classList.remove('input-error');
                if (label) label.classList.remove('text-error');
            }
        }
    });

    if (missingFields.length > 0) {
        Swal.fire({
            title: 'Campos incompletos',
            text: 'Por favor completa los siguientes campos: ' + missingFields.join(', '),
            icon: 'warning',
            confirmButtonText: 'Aceptar',
            customClass: {
                confirmButton: 'classbotones'
            }
        });
        return;
    }

    // Función para convertir imagen a WebP
    function convertImageToWebP(file, quality = 0.8) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function(event) {
                const img = new Image();
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                    canvas.toBlob(
                        (blob) => {
                            if (blob) {
                                const webpFile = new File([blob], file.name.replace(/\.[^/.]+$/, ".webp"), { type: "image/webp" });
                                resolve(webpFile);
                            } else {
                                reject(new Error('No se pudo convertir la imagen a WebP'));
                            }
                        },
                        'image/webp',
                        quality
                    );
                };
                img.onerror = reject;
                img.src = event.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    const formData = new FormData();
    formData.append("Nombre", document.getElementById('Nombreedit').value);
    formData.append("Descripcion", document.getElementById('Descripcionedit').value);
    formData.append("CategoriaId", document.getElementById('CategoriaIdedit').value);
    formData.append("UnidadMedidaId", document.getElementById('UnidadMedidaIdedit').value);
    formData.append("MarcaId", document.getElementById('MarcaIdedit').value);
    formData.append("CodigoSKU", document.getElementById('CodigoSKUedit').value);
    formData.append("ImagenNombreActual", document.getElementById('ImagenNombreActual').value);
    formData.append("ImagenUrlActual", document.getElementById('ImagenUrlActual').value);
    formData.append("precioVenta", document.getElementById('precioVentaedit').value);

    const isActiveCheckbox = document.getElementById("isActiveedit");
    formData.append("IsActive", isActiveCheckbox.checked);

    const vencimientoCheckbox = document.getElementById("vencimientoedit");
    formData.append("Vencimiento", vencimientoCheckbox.checked);

    const imagenInput = document.getElementById("imagenproductoedit");
    if (imagenInput.files && imagenInput.files[0]) {
        const file = imagenInput.files[0];
        const fileExtension = file.name.split('.').pop().toLowerCase();

        if (!["jpg", "jpeg", "png", "webp"].includes(fileExtension)) {
            Swal.fire({
                title: 'Archivo no válido',
                text: 'Por favor, sube una imagen en formato JPG o PNG.',
                icon: 'error',
                confirmButtonText: 'Aceptar',
                customClass: { confirmButton: 'custom-alertas-button' }
            });
            return;
        }

        try {
            const webpFile = await convertImageToWebP(file);
            formData.append("Imagen", webpFile);
        } catch (error) {
            Swal.fire({
                title: 'Error',
                text: 'No se pudo procesar la imagen.',
                icon: 'error',
                confirmButtonText: 'Aceptar',
                customClass: { confirmButton: 'custom-alertas-button' }
            });
            return;
        }
    }

    try {
        const response = await fetch(`/manager/productos/put/${Id}/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
                "X-HTTP-Method-Override": "PUT"
            },
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            Swal.fire({
                title: "¡Éxito!",
                text: data.message || "Actualizado correctamente",
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
        Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado. Ver consola para más detalles.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" }
        });
        console.error(error);
    }
});


//----------------------
// ELIMINACION
//----------------------
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
                    const response = await fetch(`/manager/productos/delete/${userId}/`, {
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

//----------------
// INPUT SELECT 
//----------------
/*--------------------------------------*/
/* FUNCIÓN DE DEBOUNCE */
// Permite que la búsqueda no se haga en cada tecla, sino tras 300ms de espera
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

/*--------------------------------------*/
/* FETCH DE CATEGORÍAS */
async function fetchCategorias(term, optionsContainer) {
    if (term.length < 2) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">
                Escriba al menos 2 letras
            </div>`;
        return;
    }

    try {
        const res = await fetch(`/manager/categorias/search/?search=${encodeURIComponent(term)}`);
        const data = await res.json();

        optionsContainer.innerHTML = "";

        if (data.length === 0) {
            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Sin resultados</div>`;
            return;
        }

        data.forEach(c => {
            optionsContainer.innerHTML += `
                <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${c.id}">
                    ${c.nombre}
                </button>`;
        });
    } catch (error) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">Error al buscar categorías</div>`;
        console.error(error);
    }
}
/* FETCH DE UMedidas */
async function fetchUMedidas(term, optionsContainer) {
    if (term.length < 2) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">
                Escriba al menos 2 letras
            </div>`;
        return;
    }

    const res = await fetch(`/manager/presentaciones/search/?search=${encodeURIComponent(term)}`);
    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (data.length === 0) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">Sin resultados</div>`;
        return;
    }

    data.forEach(u => {
        optionsContainer.innerHTML += `
            <button type="button"
                    class="list-group-item list-group-item-action"
                    data-value="${u.id}">
                ${u.nombre} | ${u.abreviatura}
            </button>`;
    });
}

async function fetchMarcas(term, optionsContainer) {
    if (term.length < 2) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">
                Escriba al menos 2 letras
            </div>`;
        return;
    }

    const res = await fetch(`/manager/marcas/search/?search=${encodeURIComponent(term)}`);
    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (data.length === 0) {
        optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">Sin resultados</div>`;
        return;
    }

    data.forEach(m => {
        optionsContainer.innerHTML += `
            <button type="button"
                    class="list-group-item list-group-item-action"
                    data-value="${m.id}">
                ${m.nombre}
            </button>`;
    });
}


/*--------------------------------------*/
/* INIT DROPDOWN */
function initDropdown(hiddenInputId, remoteSearchFn = null) {
    const hiddenInput = document.getElementById(hiddenInputId);
    const container = hiddenInput.nextElementSibling; 
    const selectBtn = container.querySelector("button");
    const dropdown = container.querySelector(".dropdown-menu");
    const searchInput = container.querySelector(".search-box input");
    const optionsContainer = container.querySelector(".options");

    // Selección de opción
    optionsContainer.addEventListener("click", (e) => {
        if (e.target.matches(".list-group-item")) {
            hiddenInput.value = e.target.dataset.value;
            selectBtn.textContent = e.target.textContent;
            dropdown.classList.remove("show");
            searchInput.value = "";
        }
    });

    // Abrir/ocultar dropdown
    selectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("show");
        searchInput.focus();

        if (remoteSearchFn) {
            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    Escriba al menos 2 letras
                </div>`;
        }
    });

    // Buscar mientras escribe (solo si tiene función remota)
    searchInput.addEventListener("input", debounce(() => {
        if (remoteSearchFn) {
            remoteSearchFn(searchInput.value.trim(), optionsContainer);
        }
    }, 300));

    // Cerrar dropdown al hacer click fuera
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".select-container")) {
            dropdown.classList.remove("show");
        }
    });

    return { hiddenInput, selectBtn, optionsContainer };
}

/*--------------------------------------*/
/* INICIALIZACIÓN DE DROPDOWNS */
initDropdown("CategoriaId", fetchCategorias); // Categoría con búsqueda remota
initDropdown("UnidadMedidaId", fetchUMedidas);               // Otros sin búsqueda remota
initDropdown("MarcaId", fetchMarcas);
initDropdown("CategoriaIdedit", fetchCategorias);
initDropdown("UnidadMedidaIdedit", fetchUMedidas);
initDropdown("MarcaIdedit", fetchMarcas);


//----------------
// INPUT FILE 
//----------------
document.addEventListener('DOMContentLoaded', function () {
  // Selecciona todos los contenedores con clase 'file-drop-area'
  var fileDropAreas = document.querySelectorAll('.file-drop-area');

  fileDropAreas.forEach(function(fileDropArea) {
      var fileInput = fileDropArea.querySelector('input[type="file"]');
      var fileMessage = fileDropArea.querySelector('.file-message');

      // Asegurarnos de que los eventos se aplican solo una vez
      if (fileInput && fileMessage) {
          // Evitar el comportamiento por defecto para eventos de arrastrar y soltar
          fileDropArea.addEventListener('dragover', function (e) {
              e.preventDefault();
              e.stopPropagation();
              fileDropArea.classList.add('dragover');
          });

          fileDropArea.addEventListener('dragleave', function (e) {
              e.preventDefault();
              e.stopPropagation();
              fileDropArea.classList.remove('dragover');
          });

          fileDropArea.addEventListener('drop', function (e) {
              e.preventDefault();
              e.stopPropagation();
              fileDropArea.classList.remove('dragover');

              var files = e.dataTransfer.files; // Obtener los archivos arrastrados
              if (files.length > 0) {
                  fileInput.files = files; // Asignar archivos al input file
                  fileMessage.textContent = files[0].name; // Mostrar el nombre del archivo
              }
          });

          // Mostrar el nombre del archivo seleccionado manualmente
          fileInput.addEventListener('change', function () {
              if (fileInput.files.length > 0) {
                  fileMessage.textContent = fileInput.files[0].name;
              } else {
                  fileMessage.textContent = "Arrastra tu archivo aquí o haz clic para seleccionar";
              }
          });
      }
  });
});



document.addEventListener('DOMContentLoaded', () => {
    const vencimientoCheckbox = document.getElementById('vencimiento');
    const vencimientoText = document.getElementById('vencimientoText');

    if (vencimientoCheckbox && vencimientoText) {
        const toggleVencimientoText = () => {
            if (vencimientoCheckbox.checked) {
                vencimientoText.textContent = 'Si';
                vencimientoText.classList.remove('text-danger');
                vencimientoText.classList.add('text-success');
            } else {
                vencimientoText.textContent = 'No';
                vencimientoText.classList.remove('text-success');
                vencimientoText.classList.add('text-danger');
            }
        };

        toggleVencimientoText(); // Inicializa el texto
        vencimientoCheckbox.addEventListener('change', toggleVencimientoText);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const vencimientoCheckbox = document.getElementById('vencimientoedit');
    const vencimientoText = document.getElementById('vencimientoTextedit');

    if (vencimientoCheckbox && vencimientoText) {
        const toggleVencimientoText = () => {
            if (vencimientoCheckbox.checked) {
                vencimientoText.textContent = 'Si';
                vencimientoText.classList.remove('text-danger');
                vencimientoText.classList.add('text-success');
            } else {
                vencimientoText.textContent = 'No';
                vencimientoText.classList.remove('text-success');
                vencimientoText.classList.add('text-danger');
            }
        };

        toggleVencimientoText(); // Inicializa el texto
        vencimientoCheckbox.addEventListener('change', toggleVencimientoText);
    }
});






