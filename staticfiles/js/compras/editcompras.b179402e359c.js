let productosSeleccionadosGlobal = {};

document.addEventListener("DOMContentLoaded", () => {
    const buscador = document.getElementById("buscadorProductos");

    cargarProductos();

    buscador.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            cargarProductos(1, buscador.value.trim());
        }
    });

    document.getElementById("guardarProductosSeleccionados").addEventListener("click", () => {
        agregarProductosSeleccionados();
    });

    document.querySelector("#tablacont").addEventListener("click", function (e) {
        const boton = e.target.closest(".eliminar-fila");
        if (!boton) return;

        const fila = boton.closest("tr");
        if (!fila) return;

        const idProducto = fila.id.replace("producto-row-", "");
        fila.remove();

        // Eliminar también del estado global
        delete productosSeleccionadosGlobal[idProducto];

        // Deseleccionar en el modal
        const checkbox = document.querySelector(`.producto-checkbox[value="${idProducto}"]`);
        if (checkbox) {
            checkbox.checked = false;
            const productoItem = checkbox.closest(".producto-item");
            if (productoItem) {
                productoItem.classList.remove("seleccionado");
            }
        }

        reordenarTabla();
        actualizarTotales();
    });

    if (typeof compra !== "undefined" && compra) {
        cargarCompraEnFormulario(compra);
    }
});



function cargarCompraEnFormulario(compra) {
    // --- Seleccionar proveedor ---
    const proveedorInput = document.getElementById("proveedoresidedit");
    if (proveedorInput) {
        proveedorInput.value = compra.proveedorId;
        const selectBtn = proveedorInput.nextElementSibling?.querySelector("button");
        if (selectBtn) {
            selectBtn.textContent = compra.proveedorNombre || "Seleccione un proveedor";
        }
    }

    const recepcionInput = document.getElementById("recepcionidedit");
    if (recepcionInput) {
        recepcionInput.value = compra.ubicacionId;
        const selectBtn = recepcionInput.nextElementSibling?.querySelector("button");
        if (selectBtn) {
            selectBtn.textContent = compra.ubicacionNombre || "Seleccione una recepción";
        }
    }


    // --- Limpiar estado y tabla ---
    productosSeleccionadosGlobal = {};
    const tablaBody = document.querySelector("#tablacont tbody");
    tablaBody.innerHTML = "";

    // --- Insertar productos de la compra ---
    compra.detalles.forEach((detalle, index) => {
        const id = detalle.productoId;

        productosSeleccionadosGlobal[id] = {
            nombre: detalle.productoNombre,
            presentacion: detalle.presentacion,
            sku: detalle.sku,
            cantidad: detalle.cantidad,
            precio: detalle.precioCompra
        };

        const fila = document.createElement("tr");
        fila.id = `producto-row-${id}`;
        fila.innerHTML = `
            <td>${index + 1}</td>
            <td>${detalle.productoNombre}</td>
            <td>${detalle.presentacion}</td>
            <td>${detalle.sku}</td>
            <td>
                <input type="number" min="0" step="0.01" class="form-control precio-input" 
                       name="precio_${id}" value="${detalle.precioCompra}" required>
            </td>
            <td>
                <input type="number" min="1" step="1" class="form-control cantidad-input" 
                       name="cantidad_${id}" value="${detalle.cantidad}" required>
            </td>
            <td>
                <button type="button" class="btn btn-danger btn-sm eliminar-fila">
                    <i class='bx bx-trash'></i>
                </button>
            </td>
        `;
        tablaBody.appendChild(fila);
    });

    inicializarEventosInputsTotales();
    actualizarTotales();

    // --- Marcar en el modal ---
    setTimeout(() => {
        compra.detalles.forEach(detalle => {
            const checkbox = document.querySelector(`.producto-checkbox[value="${detalle.productoId}"]`);
            if (checkbox) {
                checkbox.checked = true;
                checkbox.closest(".producto-item")?.classList.add("seleccionado");
            }
        });
    }, 500); // Esperamos un poco a que cargue el modal
}


async function cargarProductos(page = 1, search = "") {
    const contenedor = document.getElementById("contenedorProductosAjax");
    const paginacion = document.getElementById("paginacionProductos");

    let loadingDiv = contenedor.querySelector("#loadingProductos");
    if (!loadingDiv) {
        loadingDiv = document.createElement("div");
        loadingDiv.id = "loadingProductos";
        loadingDiv.className = "text-center py-4";
        loadingDiv.textContent = "Cargando productos...";
        contenedor.prepend(loadingDiv);
    }
    loadingDiv.style.display = "block";

    paginacion.innerHTML = "";

    try {
        const url = new URL(`/manager/api/proxy/productos/`, window.location.origin);
        url.searchParams.append("page", page);
        url.searchParams.append("limit", 10);
        if (search) url.searchParams.append("search", search);

        const response = await fetch(url);

        if (!response.ok) throw new Error("Error al obtener productos");

        const data = await response.json();

        loadingDiv.style.display = "none";

        let productosDiv = contenedor.querySelector("#productos-lista");
        if (!productosDiv) {
            productosDiv = document.createElement("div");
            productosDiv.id = "productos-lista";
            productosDiv.style.maxHeight = "400px";
            productosDiv.style.overflowY = "auto";
            contenedor.appendChild(productosDiv);
        }
        productosDiv.innerHTML = "";

        data.results.forEach(prod => {
            const div = document.createElement("div");
            div.className = "productosstyle producto-item d-flex align-items-center w-100";
            div.dataset.id = prod.id;
            div.dataset.nombre = prod.nombre.toLowerCase();
            div.dataset.presentacion = prod.unidadMedida.nombre.toLowerCase();
            div.dataset.sku = prod.codigoSKU.toLowerCase();

            div.innerHTML = `
                <div class="me-3">
                    <img src="${prod.imagenUrl}" alt="${prod.nombre}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 5px;">
                </div>
                <div class="flex-grow-1">
                    <strong>${prod.nombre}</strong><br>
                    <small>${prod.unidadMedida.nombre} | SKU: ${prod.codigoSKU}</small>
                </div>
                <input type="checkbox" class="form-check-input producto-checkbox d-none" value="${prod.id}">
            `;

            productosDiv.appendChild(div);
        });

        renderPaginacion(data.page, data.totalPages, search);

    } catch (error) {
        loadingDiv.style.display = "none";
        contenedor.innerHTML = `<p class="text-danger text-center py-4">${error.message}</p>`;
    }

    inicializarSeleccionProductos();
}


function inicializarSeleccionProductos() {
    document.querySelectorAll(".producto-item").forEach(prod => {
        const checkbox = prod.querySelector(".producto-checkbox");
        const id = checkbox.value;

        // Restaurar selección desde el global
        if (productosSeleccionadosGlobal[id]) {
            checkbox.checked = true;
            prod.classList.add("seleccionado");
        }

        prod.addEventListener("click", () => {
            checkbox.checked = !checkbox.checked;
            prod.classList.toggle("seleccionado", checkbox.checked);

            if (checkbox.checked) {
                productosSeleccionadosGlobal[id] = {
                    nombre: prod.dataset.nombre,
                    presentacion: prod.dataset.presentacion,
                    sku: prod.dataset.sku
                };
            } else {
                delete productosSeleccionadosGlobal[id];
            }
        });
    });
}


function renderPaginacion(currentPage, totalPages, search) {
    const paginacion = document.getElementById("paginacionProductos");
    paginacion.innerHTML = "";

    let startPage = Math.max(currentPage - 2, 1);
    let endPage = startPage + 4;
    if (endPage > totalPages) {
        endPage = totalPages;
        startPage = Math.max(endPage - 4, 1);
    }

    const liPrev = document.createElement("li");
    liPrev.classList.add("page-item");
    if (currentPage === 1) liPrev.classList.add("disabled");
    liPrev.innerHTML = `<a class="page-link" href="#">«</a>`;
    liPrev.addEventListener("click", e => {
        e.preventDefault();
        if (currentPage > 1) cargarProductos(currentPage - 1, search);
    });
    paginacion.appendChild(liPrev);

    for (let p = startPage; p <= endPage; p++) {
        const li = document.createElement("li");
        li.classList.add("page-item");
        if (p === currentPage) li.classList.add("active");
        li.innerHTML = `<a class="page-link" href="#">${p}</a>`;
        li.addEventListener("click", e => {
            e.preventDefault();
            if (p !== currentPage) cargarProductos(p, search);
        });
        paginacion.appendChild(li);
    }

    const liNext = document.createElement("li");
    liNext.classList.add("page-item");
    if (currentPage === totalPages) liNext.classList.add("disabled");
    liNext.innerHTML = `<a class="page-link" href="#">»</a>`;
    liNext.addEventListener("click", e => {
        e.preventDefault();
        if (currentPage < totalPages) cargarProductos(currentPage + 1, search);
    });
    paginacion.appendChild(liNext);
}

function agregarProductosSeleccionados() {
    const tablaBody = document.querySelector("#tablacont tbody");

    Object.entries(productosSeleccionadosGlobal).forEach(([id, data]) => {
        if (document.querySelector(`#producto-row-${id}`)) return;

        const fila = document.createElement("tr");
        fila.id = `producto-row-${id}`;
        fila.innerHTML = `
            <td></td>
            <td>${data.nombre}</td>
            <td>${data.presentacion}</td>
            <td>${data.sku}</td>
            <td>
                <input type="number" min="0" step="0.01" class="form-control precio-input" name="precio_${id}" required>
            </td>
            <td>
                <input type="number" min="1" step="1" class="form-control cantidad-input" name="cantidad_${id}" value="1" required>
            </td>
            <td>
                <button type="button" class="btn btn-danger btn-sm eliminar-fila">
                    <i class='bx bx-trash'></i>
                </button>
            </td>
        `;
        tablaBody.appendChild(fila);
        inicializarEventosInputsTotales();
    });

    reordenarTabla();
    actualizarTotales();

    const modal = bootstrap.Modal.getInstance(document.getElementById("modalregis"));
    modal.hide();
}


function reordenarTabla() {
    const tablaBody = document.querySelector("#tablacont tbody");
    if (!tablaBody) return;
    const filas = tablaBody.querySelectorAll("tr");
    filas.forEach((fila, index) => {
        const primeraCelda = fila.querySelector("td:first-child");
        if (primeraCelda) {
            primeraCelda.textContent = index + 1;
        }
    });
}

function actualizarTotales() {
    let total = 0;
    let contador = 0;
    let cantidadTotal = 0;

    const tablaBody = document.querySelector("#tablacont tbody");
    if (!tablaBody) return;

    tablaBody.querySelectorAll("tr").forEach(fila => {
        const precioInput = fila.querySelector('input.precio-input');
        const cantidadInput = fila.querySelector('input.cantidad-input');

        const precio = parseFloat(precioInput?.value) || 0;
        const cantidad = parseInt(cantidadInput?.value) || 0;

        total += precio * cantidad;
        contador++;
        cantidadTotal += cantidad;
    });

    document.getElementById("total-compra").textContent = `Total: L. ${total.toFixed(2)}`;
    document.getElementById("contador-productos").textContent = `Productos: ${contador}`;
    document.getElementById("cantidad-productos").textContent = `Total de productos: ${cantidadTotal}`;
}

function inicializarEventosInputsTotales() {
    const tablaBody = document.querySelector("#tablacont tbody");
    if (!tablaBody) return;

    tablaBody.querySelectorAll("input.precio-input, input.cantidad-input").forEach(input => {
        input.removeEventListener("input", actualizarTotales);
        input.addEventListener("input", actualizarTotales);
    });
}




let modalDetallesArray = [];
const MODAL_PAGE_SIZE = 10;

// Al hacer clic en el botón de confirmar compra
document.getElementById("toggleDropdownPanel32").addEventListener("click", function () {
    const proveedorId = document.getElementById("proveedoresidedit").value;
    const recepcionId = document.getElementById("recepcionidedit").value;
    const productosSeleccionados = document.querySelectorAll("#tablacont tbody tr");

    let errores = [];

    if (!recepcionId) {
        errores.push("Debe seleccionar una ubicación de recepción.");
    }

    if (!proveedorId) {
        errores.push("Debe seleccionar un proveedor.");
    }

    if (productosSeleccionados.length === 0) {
        errores.push("Debe agregar al menos un producto.");
    }

    productosSeleccionados.forEach((fila, index) => {
        const precio = fila.querySelector(".precio-input").value.trim();
        const cantidad = fila.querySelector(".cantidad-input").value.trim();

        if (!precio || isNaN(precio) || parseFloat(precio) <= 0) {
            errores.push(`Precio inválido en el producto #${index + 1}`);
        }

        if (!cantidad || isNaN(cantidad) || parseInt(cantidad) <= 0) {
            errores.push(`Cantidad inválida en el producto #${index + 1}`);
        }
    });

    if (errores.length > 0) {
        Swal.fire({
            title: "Campos incompletos",
            html: errores.join("<br>"),
            icon: "warning",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" }
        });
        return;
    }

    // Construir los detalles que se mostrarán en el modal
    modalDetallesArray = [];
    productosSeleccionados.forEach((fila, index) => {
        const productoId = fila.id.replace("producto-row-", "");
        const nombre = fila.children[1].textContent.trim();
        const presentacion = fila.children[2].textContent.trim();
        const sku = fila.children[3].textContent.trim();
        const precio = parseFloat(fila.querySelector(".precio-input").value) || 0;
        const cantidad = parseInt(fila.querySelector(".cantidad-input").value) || 0;

        modalDetallesArray.push({
            productoId,
            nombre,
            presentacion,
            sku,
            precio,
            cantidad,
            total: precio * cantidad
        });
    });

    // Mostrar la primera página en el modal
    mostrarPaginaComprar(1);

    // Abrir modal con bootstrap
    const modalElement = document.getElementById("completarcompra");
    document.getElementById("tcompra").value = compra.tipoCompra ?? "";
    document.getElementById("observaciones").value = compra.observaciones ?? "";
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
});

// Función para renderizar la tabla del modal con paginación
function mostrarPaginaComprar(page = 1) {
    const tablaModal = document.getElementById("tablaDetallesModal");
    const pagDiv = document.getElementById("paginadorcomprar");

    const totalItems = modalDetallesArray.length;
    const totalPages = Math.ceil(totalItems / MODAL_PAGE_SIZE) || 1;
    page = Math.max(1, Math.min(page, totalPages));

    const start = (page - 1) * MODAL_PAGE_SIZE;
    const end = start + MODAL_PAGE_SIZE;
    const items = modalDetallesArray.slice(start, end);

    // Limpiar y agregar filas
    tablaModal.innerHTML = "";
    items.forEach((prod, idx) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${start + idx + 1}</td>
            <td>${prod.nombre}</td>
            <td>${prod.presentacion}</td>
            <td>${prod.sku}</td>
            <td>${prod.cantidad}</td>
            <td>L. ${prod.precio.toFixed(2)}</td>
        `;
        tablaModal.appendChild(tr);
    });

    // Renderizar paginación
    pagDiv.innerHTML = "";
    const ul = document.createElement("ul");
    ul.className = "pagination";

    const crearLi = (text, disabled, onclick) => {
        const li = document.createElement("li");
        li.className = "page-item" + (disabled ? " disabled" : "");
        li.innerHTML = `<a class="page-link" href="#">${text}</a>`;
        if (!disabled) {
            li.addEventListener("click", e => { e.preventDefault(); onclick(); });
        }
        return li;
    };

    ul.appendChild(crearLi("«", page === 1, () => mostrarPaginaComprar(page - 1)));
    for (let p = 1; p <= totalPages; p++) {
        const li = document.createElement("li");
        li.className = "page-item" + (p === page ? " active" : "");
        li.innerHTML = `<a class="page-link" href="#">${p}</a>`;
        li.addEventListener("click", e => { e.preventDefault(); mostrarPaginaComprar(p); });
        ul.appendChild(li);
    }
    ul.appendChild(crearLi("»", page === totalPages, () => mostrarPaginaComprar(page + 1)));

    pagDiv.appendChild(ul);
}

//----------------
// INPUT SELECT 
//----------------
// Función debounce
function debounce(func, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
    };
}

// Inicialización del dropdown
function initDropdown(hiddenInputId, remoteSearchFn = null) {
    const hiddenInput = document.getElementById(hiddenInputId);
    const container = hiddenInput.nextElementSibling;
    const selectBtn = container.querySelector("button");
    const dropdown = container.querySelector(".dropdown-menu");
    const searchInput = container.querySelector(".search-box input");
    const optionsContainer = container.querySelector(".options");

    // Selección
    optionsContainer.addEventListener("click", (e) => {
        if (e.target.matches(".list-group-item")) {
            hiddenInput.value = e.target.dataset.value;
            selectBtn.textContent = e.target.textContent;
            dropdown.classList.remove("show");
            searchInput.value = "";
        }
    });

    // Abrir dropdown
    selectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdown.classList.toggle("show");
        searchInput.focus();

        if (remoteSearchFn) {
            optionsContainer.innerHTML = `<div class="list-group-item text-muted">Escriba al menos 2 letras</div>`;
        }
    });

    // Búsqueda remota
    searchInput.addEventListener("input", debounce(() => {
        if (remoteSearchFn) remoteSearchFn(searchInput.value.trim(), optionsContainer);
    }, 300));

    // Cerrar al hacer click fuera
    document.addEventListener("click", (e) => {
        if (!e.target.closest(".select-container")) {
            dropdown.classList.remove("show");
        }
    });

    return { hiddenInput, selectBtn, optionsContainer };
}

// Fetch remoto proveedores
async function fetchProveedores(term, optionsContainer) {
    if (term.length < 2) {
        optionsContainer.innerHTML = `<div class="list-group-item text-muted">Escriba al menos 2 letras</div>`;
        return;
    }

    const res = await fetch(`/manager/proveedores/search/?search=${encodeURIComponent(term)}`);
    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
        optionsContainer.innerHTML = `<div class="list-group-item text-muted">Sin resultados</div>`;
        return;
    }

    data.forEach(p => {
        optionsContainer.innerHTML += `
            <button type="button" class="list-group-item list-group-item-action" data-value="${p.id}">
                ${p.nombreLegal} ${p.nombreComercial ? '| ' + p.nombreComercial : ''}
            </button>
        `;
    });
}

async function fetchUbicaciones(term, optionsContainer) {
    if (term.length < 2) {
        optionsContainer.innerHTML = `<div class="list-group-item text-muted">Escriba al menos 2 letras</div>`;
        return;
    }

    const res = await fetch(`/manager/ubicaciones/search/?search=${encodeURIComponent(term)}`);
    const data = await res.json();  


    optionsContainer.innerHTML = "";

    if (!data.length) {
        optionsContainer.innerHTML = `<div class="list-group-item text-muted">Sin resultados</div>`;
        return;
    }

    data.forEach(p => {
        optionsContainer.innerHTML += `
            <button type="button" class="list-group-item list-group-item-action" data-value="${p.id}">
                ${p.nombre} ${p.codigo ? '| ' + p.tipo : ''}
            </button>
        `;
    });

}

// Inicializar
initDropdown("proveedoresidedit", fetchProveedores);
initDropdown("recepcionidedit", fetchUbicaciones);

document.getElementById("enviarCompraBtn").addEventListener("click", async function () {
    const proveedorId = parseInt(document.getElementById("proveedoresidedit").value);
    const recepcionId = parseInt(document.getElementById("recepcionidedit").value);
    const tipoCompraValue = parseInt(document.getElementById("tcompra").value);
    const observaciones = document.getElementById("observaciones").value.trim();
    const COMPRA_ID = document.getElementById("compraid").value;

    const detalles = Array.from(document.querySelectorAll("#tablacont tbody tr")).map(fila => ({
        productoId: parseInt(fila.id.replace("producto-row-", "")),
        cantidad: parseInt(fila.querySelector(".cantidad-input").value),
        precioCompra: parseFloat(fila.querySelector(".precio-input").value)
    }));

    const payload = { proveedorId, tipoCompra: tipoCompraValue, observaciones, detalles, recepcionId };

    try {
        const response = await fetch(`/manager/compras/put/${COMPRA_ID}/`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            Swal.fire({
                title: "¡Éxito!",
                text: data.message,
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            }).then(() => window.location.href = "/manager/compras/");
        } else {
            throw new Error(data.message || "Error al actualizar la compra");
        }
    } catch (err) {
        Swal.fire({
            title: "Error",
            text: err.message,
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" }
        });
    }
});
