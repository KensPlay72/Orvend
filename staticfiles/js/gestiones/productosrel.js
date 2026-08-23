//----------------
// INPUT SELECT SMART SEARCH
//----------------

// Función debounce
function debounce(func, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

// Inicialización genérica del dropdown
function initDropdown(hiddenInputId, remoteSearchFn = null) {
  const hiddenInput = document.getElementById(hiddenInputId);
  const container = hiddenInput.nextElementSibling;
  const selectBtn = container.querySelector("button");
  const dropdown = container.querySelector(".dropdown-menu");
  const searchInput = container.querySelector(".search-box input");
  const optionsContainer = container.querySelector(".options");

  // Seleccionar opción
  optionsContainer.addEventListener("click", (e) => {
    const item = e.target.closest(".list-group-item");
    if (item) {
      hiddenInput.value = item.dataset.value;
      selectBtn.textContent = item.dataset.label;
      dropdown.classList.remove("show");
      searchInput.value = "";
    }
  });

  // Abrir dropdown y cargar sugerencias
  selectBtn.addEventListener("click", async (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("show");
    searchInput.focus();

    if (dropdown.classList.contains("show") && remoteSearchFn) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Cargando sugerencias...</div>
            `;
      await remoteSearchFn("", optionsContainer);
    }
  });

  // Buscar mientras escribe
  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Buscando...</div>
            `;
        remoteSearchFn(searchInput.value.trim(), optionsContainer);
      }
    }, 300),
  );

  // Cerrar al hacer click fuera
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });

  return { hiddenInput, selectBtn, optionsContainer };
}

// =====================================================
// PRODUCTOS PADRE
// =====================================================

async function fetchProductosPadre(term, optionsContainer) {

    try {

        const response = await fetch(
            "/manager/api/proxy/productos/padre/"
        );

        if (!response.ok) {

            throw new Error(
                `Error HTTP: ${response.status}`
            );

        }

        const data = await response.json();

        // Limpiar resultados anteriores
        optionsContainer.innerHTML = "";


        // =====================================================
        // VALIDAR RESPUESTA
        // =====================================================

        if (
            !data.success ||
            !Array.isArray(data.productos) ||
            data.productos.length === 0
        ) {

            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    No hay productos padre disponibles
                </div>
            `;

            return;
        }


        // =====================================================
        // FILTRAR
        // =====================================================

        const termino = term
            .toLowerCase()
            .trim();


        const productos = data.productos.filter((producto) => {

            const nombre = (
                producto.nombre || ""
            ).toLowerCase();

            const sku = (
                producto.codigoSKU || ""
            ).toLowerCase();

            return (
                nombre.includes(termino) ||
                sku.includes(termino)
            );

        });


        // =====================================================
        // SIN RESULTADOS
        // =====================================================

        if (productos.length === 0) {

            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    No se encontraron productos
                </div>
            `;

            return;
        }


        // =====================================================
        // OPCIONES
        // =====================================================

        productos.forEach((producto) => {

            const nombre = producto.nombre || "";
            const sku = producto.codigoSKU || "";

            const texto = `${nombre} | ${sku}`;


            optionsContainer.innerHTML += `
                <button
                    type="button"
                    class="list-group-item list-group-item-action"
                    data-value="${producto.id}"
                    data-label="${texto}"
                >
                    <strong>${nombre}</strong>

                    <small class="text-muted">
                        | ${sku}
                    </small>
                </button>
            `;

        });


    } catch (error) {

        console.error(
            "Error al cargar productos padre:",
            error
        );


        optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">
                Error al cargar productos padre
            </div>
        `;

    }

}



// =====================================================
// PRODUCTOS HIJOS
// =====================================================

async function fetchProductosHijos(term, optionsContainer) {

    try {

        const response = await fetch(
            "/manager/api/proxy/productos/hijos/"
        );

        if (!response.ok) {

            throw new Error(
                `Error HTTP: ${response.status}`
            );

        }

        const data = await response.json();

        // Limpiar resultados anteriores
        optionsContainer.innerHTML = "";


        // =====================================================
        // VALIDAR RESPUESTA
        // =====================================================

        if (
            !data.success ||
            !Array.isArray(data.productos) ||
            data.productos.length === 0
        ) {

            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    No hay productos hijos disponibles
                </div>
            `;

            return;
        }


        // =====================================================
        // FILTRAR
        // =====================================================

        const termino = term
            .toLowerCase()
            .trim();


        const productos = data.productos.filter((producto) => {

            const nombre = (
                producto.nombre || ""
            ).toLowerCase();

            const sku = (
                producto.codigoSKU || ""
            ).toLowerCase();

            return (
                nombre.includes(termino) ||
                sku.includes(termino)
            );

        });


        // =====================================================
        // SIN RESULTADOS
        // =====================================================

        if (productos.length === 0) {

            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    No se encontraron productos
                </div>
            `;

            return;
        }



        // =====================================================
        // OPCIONES
        // =====================================================

        productos.forEach((producto) => {

            const nombre = producto.nombre || "";
            const sku = producto.codigoSKU || "";

            const texto = `${nombre} | ${sku}`;


            optionsContainer.innerHTML += `
                <button
                    type="button"
                    class="list-group-item list-group-item-action"
                    data-value="${producto.id}"
                    data-label="${texto}"
                >
                    <strong>${nombre}</strong>

                    <small class="text-muted">
                        | ${sku}
                    </small>
                </button>
            `;

        });


    } catch (error) {

        console.error(
            "Error al cargar productos hijos:",
            error
        );


        optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">
                Error al cargar productos hijos
            </div>
        `;

    }

}



// =====================================================
// INICIALIZAR DROPDOWNS
// =====================================================
//
// IMPORTANTE:
// initDropdown() está en OTRO archivo.
// Ese archivo debe cargarse antes que este.
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        // -------------------------------------------------
        // PRODUCTO PADRE
        // -------------------------------------------------

        initDropdown(
            "producto_padre_id",
            fetchProductosPadre
        );

        initDropdown(
            "producto_padre_id_edit",
            fetchProductosPadre
        );


        // -------------------------------------------------
        // PRODUCTO HIJO
        // -------------------------------------------------

        initDropdown(
            "producto_hijo_id",
            fetchProductosHijos
        );
        
        initDropdown(
            "producto_hijo_id_edit",
            fetchProductosHijos
        );

    }
);

//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", () => {

    const form = document.getElementById("postregistro");

    const modalElement = document.getElementById("modalregis");

    const modal = new bootstrap.Modal(modalElement);


    form.addEventListener("submit", async (e) => {

        e.preventDefault();


        // =========================
        // OBTENER PRODUCTOS
        // =========================

        const productoMaster =
            document.getElementById(
                "producto_padre_id"
            ).value;

        const productoRelacionado =
            document.getElementById(
                "producto_hijo_id"
            ).value;


        // =========================
        // VALIDAR
        // =========================

        if (!productoMaster) {

            Swal.fire({
                title: "Producto padre",
                text: "Debe seleccionar un producto padre",
                icon: "warning",
                confirmButtonText: "Aceptar",
                customClass: {
                    confirmButton: "classbotones"
                }
            });

            return;
        }


        if (!productoRelacionado) {

            Swal.fire({
                title: "Producto hijo",
                text: "Debe seleccionar un producto hijo",
                icon: "warning",
                confirmButtonText: "Aceptar",
                customClass: {
                    confirmButton: "classbotones"
                }
            });

            return;
        }


        // =========================
        // PAYLOAD
        // =========================

        const payload = {

            producto_master: productoMaster,

            producto_relacionado: productoRelacionado

        };


        try {

            // =========================
            // REQUEST
            // =========================

            const response = await fetch(
                "/manager/productosrel/post/",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",

                        "X-CSRFToken":
                            document.querySelector(
                                "[name=csrfmiddlewaretoken]"
                            ).value
                    },

                    body: JSON.stringify(payload)
                }
            );


            const data = await response.json();


            // =========================
            // ÉXITO
            // =========================

            if (data.success) {

                modal.hide();

                form.reset();


                Swal.fire({
                    title: "¡Éxito!",

                    text:
                        data.message ||
                        "Relación registrada correctamente",

                    icon: "success",

                    confirmButtonText: "Aceptar",

                    customClass: {
                        confirmButton: "classbotones"
                    }

                }).then(() => {

                    window.location.reload(true);

                });


            }

            // =========================
            // ERROR
            // =========================

            else {

                Swal.fire({
                    title: "Error",

                    text:
                        data.message ||
                        "Ocurrió un error al registrar",

                    icon: "error",

                    confirmButtonText: "Aceptar",

                    customClass: {
                        confirmButton: "classbotones"
                    }
                });

            }


        } catch (error) {

            console.error(
                "Error al registrar relación:",
                error
            );


            Swal.fire({
                title: "Error",

                text:
                    "Error de conexión o inesperado. Ver consola para más detalles.",

                icon: "error",

                confirmButtonText: "Aceptar",

                customClass: {
                    confirmButton: "classbotones"
                }
            });

        }

    });

});


// =====================================================
// LLENAR FORMULARIO DE EDICIÓN
// =====================================================
document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".btn-edit").forEach((button) => {

        button.addEventListener("click", async () => {

            const productorelId =
                button.dataset.id;

            try {

                const response = await fetch(
                    `/manager/productosrel/get/${productorelId}/`
                );

                const data = await response.json();

                if (!data.success) {
                    return;
                }

                const productorel =
                    data.productosrel;


                // =================================================
                // ID DE LA RELACIÓN
                // =================================================

                document.getElementById(
                    "productorelid"
                ).value = productorel.id;


                // =================================================
                // PRODUCTO PADRE
                // =================================================

                const padreInput =
                    document.getElementById(
                        "producto_padre_id_edit"
                    );

                padreInput.value =
                    productorel.productoMasterId;


                const padreContainer =
                    padreInput.nextElementSibling;

                const padreButton =
                    padreContainer.querySelector(
                        "button"
                    );

                padreButton.textContent =
                    productorel.productoMaster;


                // =================================================
                // PRODUCTO HIJO
                // =================================================

                const hijoInput =
                    document.getElementById(
                        "producto_hijo_id_edit"
                    );

                hijoInput.value =
                    productorel.productoRelacionadoId;


                const hijoContainer =
                    hijoInput.nextElementSibling;

                const hijoButton =
                    hijoContainer.querySelector(
                        "button"
                    );

                hijoButton.textContent =
                    productorel.productoRelacionado;


                // =================================================
                // ESTADO
                // =================================================

                const isActiveCheckbox =
                    document.getElementById(
                        "isActiveedit"
                    );

                const activeText =
                    document.getElementById(
                        "activeTextedit"
                    );


                if (isActiveCheckbox && activeText) {

                    isActiveCheckbox.checked =
                        productorel.isActive;


                    if (productorel.isActive) {

                        activeText.textContent =
                            "Activo";

                        activeText.classList.remove(
                            "text-danger"
                        );

                        activeText.classList.add(
                            "text-success"
                        );

                    } else {

                        activeText.textContent =
                            "Inactivo";

                        activeText.classList.remove(
                            "text-success"
                        );

                        activeText.classList.add(
                            "text-danger"
                        );

                    }

                }

            } catch (error) {

                // No mostramos alertas ni mensajes.
                // El error simplemente se ignora.

            }

        });

    });

});


// =====================================================
// EDICION
// =====================================================

document.getElementById("putregistro").addEventListener("submit", async (e) => {

    e.preventDefault();

    // =================================================
    // ID DE LA RELACIÓN
    // =================================================

    const productorelId =
        document.getElementById("productorelid").value;


    // =================================================
    // DATOS
    // =================================================

    const payload = {

        producto_master:
            document.getElementById(
                "producto_padre_id_edit"
            ).value,

        producto_relacionado:
            document.getElementById(
                "producto_hijo_id_edit"
            ).value,

        IsActive:
            document.getElementById(
                "isActiveedit"
            ).checked

    };


    // =================================================
    // VALIDACIÓN FRONTEND
    // =================================================

    if (!payload.producto_master) {

        Swal.fire({
            title: "Error",
            text: "Debe seleccionar un producto padre",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: {
                confirmButton: "classbotones"
            }
        });

        return;
    }


    if (!payload.producto_relacionado) {

        Swal.fire({
            title: "Error",
            text: "Debe seleccionar un producto hijo",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: {
                confirmButton: "classbotones"
            }
        });

        return;
    }


    // =================================================
    // EVITAR MISMO PRODUCTO
    // =================================================

    if (
        payload.producto_master ===
        payload.producto_relacionado
    ) {

        Swal.fire({
            title: "Error",
            text: "El producto padre y el producto hijo no pueden ser el mismo",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: {
                confirmButton: "classbotones"
            }
        });

        return;
    }


    // =================================================
    // ENVIAR PUT
    // =================================================

    try {

        const response = await fetch(
            `/manager/productosrel/put/${productorelId}/`,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken":
                        document.querySelector(
                            "[name=csrfmiddlewaretoken]"
                        ).value
                },

                body: JSON.stringify(payload)
            }
        );


        const data = await response.json();


        // =================================================
        // RESPUESTA EXITOSA
        // =================================================

        if (data.success) {

            Swal.fire({
                title: "¡Éxito!",
                text:
                    data.message ||
                    "Relación actualizada correctamente",
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: {
                    confirmButton: "classbotones"
                }
            }).then(() => {

                window.location.reload(true);

            });

            return;
        }


        // =================================================
        // ERROR DEL SERVIDOR
        // =================================================

        Swal.fire({
            title: "Error",
            text:
                data.message ||
                "Ocurrió un error al actualizar la relación",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: {
                confirmButton: "classbotones"
            }
        });


    } catch (error) {

        Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: {
                confirmButton: "classbotones"
            }
        });

    }

});