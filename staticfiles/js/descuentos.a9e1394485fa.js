//----------------
// INPUT SELECT SMART SEARCH
//----------------

function debounce(func, delay) {
  let timer;

  return function (...args) {
    clearTimeout(timer);

    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

//----------------
// DROPDOWN GENERICO
//----------------

function initDropdown(hiddenInputId, remoteSearchFn = null) {
  const hiddenInput = document.getElementById(hiddenInputId);

  const container = hiddenInput.nextElementSibling;

  const selectBtn = container.querySelector("button");

  const dropdown = container.querySelector(".dropdown-menu");

  const searchInput = container.querySelector(".search-box input");

  const optionsContainer = container.querySelector(".options");

  // -------------------------
  // SELECCIONAR OPCION
  // -------------------------

  optionsContainer.addEventListener("click", (e) => {
    const item = e.target.closest(".list-group-item");

    if (item) {
      hiddenInput.value = item.dataset.value;

      selectBtn.textContent = item.dataset.label;

      dropdown.classList.remove("show");

      searchInput.value = "";
    }
  });

  // -------------------------
  // ABRIR DROPDOWN
  // -------------------------

  selectBtn.addEventListener("click", async (e) => {
    e.stopPropagation();

    dropdown.classList.toggle("show");

    searchInput.focus();

    if (dropdown.classList.contains("show") && remoteSearchFn) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    Cargando sugerencias...
                </div>
            `;

      await remoteSearchFn("", optionsContainer);
    }
  });

  // -------------------------
  // BUSCAR
  // -------------------------

  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        optionsContainer.innerHTML = `
                    <div class="list-group-item text-muted">
                        Buscando...
                    </div>
                `;

        remoteSearchFn(searchInput.value.trim(), optionsContainer);
      }
    }, 300),
  );

  // -------------------------
  // CERRAR
  // -------------------------

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });
}

//----------------
// FETCH PRODUCTOS
//----------------

async function fetchProductos(term, optionsContainer) {
  try {
    const res = await fetch(
      `/manager/productos/search/?search=${encodeURIComponent(term)}`,
    );

    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    Sin resultados
                </div>
            `;

      return;
    }

    optionsContainer.innerHTML += `
            <div class="list-group-item active bg-light text-dark fw-bold">
                ${term ? "Resultados encontrados" : "Sugerencias recientes"}
            </div>
        `;

    data.forEach((p) => {
      const texto = `
                ${p.nombre}
                ${p.codigo ? " | " + p.codigo : ""}
            `;

      optionsContainer.innerHTML += `
                <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${p.id}"
                        data-label="${texto}">

                    ${texto}

                </button>
            `;
    });
  } catch (error) {
    optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">
                Error al cargar productos
            </div>
        `;

    console.error(error);
  }
}

//----------------
// FETCH CATEGORIAS
//----------------

async function fetchCategorias(term, optionsContainer) {
  try {
    const res = await fetch(
      `/manager/categorias/search/?search=${encodeURIComponent(term)}`,
    );

    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    Sin resultados
                </div>
            `;

      return;
    }

    optionsContainer.innerHTML += `
            <div class="list-group-item active bg-light text-dark fw-bold">
                ${term ? "Resultados encontrados" : "Sugerencias recientes"}
            </div>
        `;

    data.forEach((c) => {
      const texto = `
                ${c.nombre}
            `;

      optionsContainer.innerHTML += `
                <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${c.id}"
                        data-label="${texto}">

                    ${texto}

                </button>
            `;
    });
  } catch (error) {
    optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">
                Error al cargar categorías
            </div>
        `;

    console.error(error);
  }
}

//----------------
// INICIALIZAR
//----------------

initDropdown("productoid", fetchProductos);
initDropdown("productoidedit", fetchProductos);

initDropdown("categoriaid", fetchCategorias);
initDropdown("categoriaidedit", fetchCategorias);

//----------------
// LOGICA EXCLUSIVA
//----------------

const aplicarProductos = document.getElementById("aplicar_productos");
const aplicarProductosEdit = document.getElementById("aplicar_productosedit");
const aplicarCategorias = document.getElementById("aplicar_categorias");
const aplicarCategoriasEdit = document.getElementById("aplicar_categoriasedit");

const contenedorProductos = document.getElementById("contenedor_productos");
const contenedorProductosEdit = document.getElementById(
  "contenedor_productosedit",
);

const contenedorCategorias = document.getElementById("contenedor_categorias");
const contenedorCategoriasEdit = document.getElementById(
  "contenedor_categoriasedit",
);
const esCantidad = document.getElementById("es_cantidad");
const contenedorCantidad = document.getElementById("contenedor_cantidad");
const contenedorCantidadEdit = document.getElementById(
  "contenedor_cantidadedit",
);

// Estado inicial

contenedorProductos.style.display = "none";
contenedorProductosEdit.style.display = "none";

contenedorCategorias.style.display = "none";
contenedorCategoriasEdit.style.display = "none";
contenedorCantidad.style.display = "none";
contenedorCantidadEdit.style.display = "none";

//----------------
// PRODUCTOS
//----------------

function toggleAplicarProductos(checked) {
  aplicarProductos.checked = checked;
  contenedorProductos.style.display = checked ? "block" : "none";

  if (checked) {
    aplicarCategorias.checked = false;
    contenedorCategorias.style.display = "none";
    document.getElementById("categoriaid").value = "";
  } else {
    document.getElementById("productoid").value = "";
  }
}

function toggleAplicarProductosEdit(checked) {
  aplicarProductosEdit.checked = checked;
  contenedorProductosEdit.style.display = checked ? "block" : "none";

  if (checked) {
    aplicarCategoriasEdit.checked = false;
    contenedorCategoriasEdit.style.display = "none";
    document.getElementById("categoriaidedit").value = "";
  } else {
    document.getElementById("productoidedit").value = "";
  }
}

function toggleAplicarCategorias(checked) {
  aplicarCategorias.checked = checked;
  contenedorCategorias.style.display = checked ? "block" : "none";

  if (checked) {
    aplicarProductos.checked = false;
    contenedorProductos.style.display = "none";
    document.getElementById("productoid").value = "";
  } else {
    document.getElementById("categoriaid").value = "";
  }
}

function toggleAplicarCategoriasEdit(checked) {
  aplicarCategoriasEdit.checked = checked;
  contenedorCategoriasEdit.style.display = checked ? "block" : "none";

  if (checked) {
    aplicarProductosEdit.checked = false;
    contenedorProductosEdit.style.display = "none";
    document.getElementById("productoidedit").value = "";
  } else {
    document.getElementById("categoriaidedit").value = "";
  }
}

aplicarProductos.addEventListener("change", function () {
  toggleAplicarProductos(this.checked);
});

aplicarProductosEdit.addEventListener("change", function () {
  toggleAplicarProductosEdit(this.checked);
});

//----------------
// CATEGORIAS
//----------------

aplicarCategorias.addEventListener("change", function () {
  toggleAplicarCategorias(this.checked);
});

aplicarCategoriasEdit.addEventListener("change", function () {
  toggleAplicarCategoriasEdit(this.checked);
});

//----------------
// DESCUENTO POR CANTIDAD
//----------------
if (esCantidad) {
  esCantidad.addEventListener("change", function () {
    const esPorcentaje = document.getElementById("es_porcentaje");
    const valorInput = document.getElementById("valor");
    const textoPorcentaje = document.getElementById("textoporcentaje");

    const br1 = document.getElementById("br_texto");
    const br2 = document.getElementById("br_texto2");

    const wrapPorcentaje = esPorcentaje?.closest(".form-check");
    const wrapValor = valorInput?.parentElement;

    if (this.checked) {
      // =========================
      // ACTIVADO CANTIDAD
      // =========================
      contenedorCantidad.style.display = "block";

      aplicarProductos.checked = true;
      aplicarCategorias.checked = false;

      contenedorProductos.style.display = "block";
      contenedorCategorias.style.display = "none";

      aplicarCategorias
        ?.closest(".form-check")
        ?.style?.setProperty("display", "none");

      document.getElementById("categoriaid").value = "";

      // OCULTAR PORCENTAJE + TEXTO + VALOR + BR
      if (wrapPorcentaje) wrapPorcentaje.style.display = "none";
      if (textoPorcentaje) textoPorcentaje.style.display = "none";
      if (wrapValor) wrapValor.style.display = "none";

      if (br1) br1.style.display = "none";
      if (br2) br2.style.display = "none";

      if (esPorcentaje) esPorcentaje.checked = false;
      if (valorInput) valorInput.value = "";
    } else {
      // =========================
      // DESACTIVADO CANTIDAD
      // =========================
      contenedorCantidad.style.display = "none";

      const esCuponChecked = document.getElementById("es_cupon").checked;

      const catWrap = aplicarCategorias?.closest(".form-check");
      if (catWrap) {
        catWrap.style.display = !esCuponChecked ? "block" : "none";
      }

      contenedorCategorias.style.display =
        aplicarCategorias.checked && !esCuponChecked ? "block" : "none";

      document.getElementById("cantidad_lleva").value = "";
      document.getElementById("cantidad_paga").value = "";

      // MOSTRAR PORCENTAJE + TEXTO + VALOR + BR
      if (wrapPorcentaje) wrapPorcentaje.style.display = "block";
      if (textoPorcentaje) textoPorcentaje.style.display = "block";
      if (wrapValor) wrapValor.style.display = "block";

      if (br1) br1.style.display = "block";
      if (br2) br2.style.display = "block";
    }
  });
}
// Listener para edición: DESCUENTO POR CANTIDAD (edit)
const esCantidadEdit = document.getElementById("es_cantidadedit");

if (esCantidadEdit) {
  esCantidadEdit.addEventListener("change", function () {
    const cantidadLlevaEdit = document.getElementById("cantidad_llevaedit");
    const cantidadPagaEdit = document.getElementById("cantidad_pagaedit");

    // =========================
    // ELEMENTOS PORCENTAJE
    // =========================
    const esPorcentajeEdit = document.getElementById("es_porcentajeedit");
    const valorEdit = document.getElementById("valoredit");
    const textoPorcentajeEdit = document.getElementById("textoporcentajeedit");

    const br1 = document.getElementById("br_textoedit");
    const br2 = document.getElementById("br_texto2edit");

    const wrapPorcentaje = esPorcentajeEdit?.closest(".form-check");
    const wrapValor = valorEdit?.parentElement;

    if (this.checked) {
      // =========================
      // ACTIVADO CANTIDAD
      // =========================
      if (contenedorCantidadEdit)
        contenedorCantidadEdit.style.display = "block";

      if (aplicarProductosEdit) aplicarProductosEdit.checked = true;
      if (aplicarCategoriasEdit) aplicarCategoriasEdit.checked = false;

      if (contenedorProductosEdit)
        contenedorProductosEdit.style.display = "block";

      if (contenedorCategoriasEdit)
        contenedorCategoriasEdit.style.display = "none";

      // ocultar categorías
      if (aplicarCategoriasEdit?.closest) {
        const wrap = aplicarCategoriasEdit.closest(".form-check");
        if (wrap) wrap.style.display = "none";
      }

      if (cantidadLlevaEdit)
        cantidadLlevaEdit.parentElement.style.display = "block";

      if (cantidadPagaEdit)
        cantidadPagaEdit.parentElement.style.display = "block";

      // =========================
      // OCULTAR PORCENTAJE + BR + TEXTO
      // =========================
      if (wrapPorcentaje) wrapPorcentaje.style.display = "none";
      if (wrapValor) wrapValor.style.display = "none";
      if (textoPorcentajeEdit) textoPorcentajeEdit.style.display = "none";

      if (br1) br1.style.display = "none";
      if (br2) br2.style.display = "none";

      if (esPorcentajeEdit) esPorcentajeEdit.checked = false;
      if (valorEdit) valorEdit.value = "";
    } else {
      // =========================
      // DESACTIVADO CANTIDAD
      // =========================
      if (contenedorCantidadEdit) contenedorCantidadEdit.style.display = "none";

      const esCuponEditChecked =
        document.getElementById("es_cuponedit").checked;

      if (aplicarCategoriasEdit?.closest) {
        const wrap = aplicarCategoriasEdit.closest(".form-check");
        if (wrap) {
          wrap.style.display = !esCuponEditChecked ? "block" : "none";
        }
      }

      if (contenedorCategoriasEdit)
        contenedorCategoriasEdit.style.display =
          aplicarCategoriasEdit.checked && !esCuponEditChecked
            ? "block"
            : "none";

      if (cantidadLlevaEdit) {
        cantidadLlevaEdit.parentElement.style.display = "none";
        cantidadLlevaEdit.value = "";
      }

      if (cantidadPagaEdit) {
        cantidadPagaEdit.parentElement.style.display = "none";
        cantidadPagaEdit.value = "";
      }

      // =========================
      // MOSTRAR PORCENTAJE + BR + TEXTO
      // =========================
      if (wrapPorcentaje) wrapPorcentaje.style.display = "block";
      if (wrapValor) wrapValor.style.display = "block";
      if (textoPorcentajeEdit) textoPorcentajeEdit.style.display = "block";

      if (br1) br1.style.display = "block";
      if (br2) br2.style.display = "block";
    }
  });
}
// Aplicar estado inicial para mostrar/ocultar según valores ya cargados
if (esCantidad) esCantidad.dispatchEvent(new Event("change"));
if (typeof esCantidadEdit !== "undefined" && esCantidadEdit)
  esCantidadEdit.dispatchEvent(new Event("change"));

//----------------
// CUPONES
//----------------
document.getElementById("es_cupon").addEventListener("change", function () {
  const divCodigo = document.getElementById("divcodigo");
  const inputCodigo = document.getElementById("codigo");

  if (this.checked) {
    divCodigo.style.display = "block";

    aplicarProductos.checked = true;
    aplicarCategorias.checked = false;

    contenedorProductos.style.display = "block";
    contenedorCategorias.style.display = "none";

    if (aplicarCategorias.closest(".form-check")) {
      aplicarCategorias.closest(".form-check").style.display = "none";
    }

    document.getElementById("categoriaid").value = "";
  } else {
    divCodigo.style.display = "none";
    inputCodigo.value = "";

    const esCantidadChecked = esCantidad ? esCantidad.checked : false;

    const catWrapper = aplicarCategorias?.closest?.(".form-check");
    if (catWrapper) {
      catWrapper.style.display = !esCantidadChecked ? "block" : "none";
    }

    contenedorProductos.style.display = aplicarProductos.checked
      ? "block"
      : "none";

    contenedorCategorias.style.display =
      aplicarCategorias.checked && !esCantidadChecked ? "block" : "none";
  }
});

document.getElementById("es_cuponedit").addEventListener("change", function () {
  const divCodigoEdit = document.getElementById("divcodigoedit");
  const inputCodigoEdit = document.getElementById("codigoedit");

  if (this.checked) {
    divCodigoEdit.style.display = "block";

    aplicarProductosEdit.checked = true;
    aplicarCategoriasEdit.checked = false;

    contenedorProductosEdit.style.display = "block";
    contenedorCategoriasEdit.style.display = "none";

    const catWrapper = aplicarCategoriasEdit?.closest?.(".form-check");
    if (catWrapper) {
      catWrapper.style.display = "none";
    }

    document.getElementById("categoriaidedit").value = "";
  } else {
    divCodigoEdit.style.display = "none";
    inputCodigoEdit.value = "";
    const esCantidadEditChecked =
      document.getElementById("es_cantidadedit")?.checked;
    const catWrapper = aplicarCategoriasEdit?.closest?.(".form-check");
    if (catWrapper) {
      catWrapper.style.display = !esCantidadEditChecked ? "block" : "none";
    }

    contenedorProductosEdit.style.display = aplicarProductosEdit.checked
      ? "block"
      : "none";

    contenedorCategoriasEdit.style.display =
      aplicarCategoriasEdit.checked && !esCantidadEditChecked
        ? "block"
        : "none";
  }
});
// =========================
// REGISTRAR
// =========================
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("postregistro");

  const modalElement = document.getElementById("modalregis");

  const modal = new bootstrap.Modal(modalElement);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      // =========================
      // INFORMACION GENERAL
      // =========================

      nombre: document.getElementById("nombre").value,

      descripcion: document.getElementById("descripcion").value,

      // =========================
      // CUPONES
      // =========================

      es_cupon: document.getElementById("es_cupon").checked,

      codigo: document.getElementById("codigo").value,

      // =========================
      // TIPO DESCUENTO
      // =========================

      es_porcentaje: document.getElementById("es_porcentaje").checked,

      valor: document.getElementById("valor").value,

      // =========================
      // CANTIDAD
      // =========================

      es_cantidad: document.getElementById("es_cantidad").checked,

      cantidad_lleva: document.getElementById("cantidad_lleva").value,
      cantidad_paga: document.getElementById("cantidad_paga").value,

      // =========================
      // APLICACION
      // =========================

      aplicar_productos: document.getElementById("aplicar_productos").checked,

      aplicar_categorias: document.getElementById("aplicar_categorias").checked,

      productoid: document.getElementById("productoid").value,

      categoriaid: document.getElementById("categoriaid").value,

      // =========================
      // LIMITES
      // =========================

      limite_uso: document.getElementById("limite_uso").value,

      // =========================
      // FECHAS
      // =========================

      fecha_inicio: document.getElementById("fecha_inicio").value,

      fecha_fin: document.getElementById("fecha_fin").value,

      // =========================
      // CONFIGURACIONES
      // =========================

      acumulable: document.getElementById("acumulable").checked,
    };

    try {
      const response = await fetch("/manager/descuentos/post/", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },

        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
        modal.hide();

        form.reset();

        // Reset visual dropdowns
        document.querySelectorAll(".select-container button").forEach((btn) => {
          btn.textContent = "Escriba para buscar...";
        });

        // Ocultar campos
        $("#divcodigo").hide();

        $("#contenedor_productos").hide();

        $("#contenedor_categorias").hide();

        Swal.fire({
          title: "¡Éxito!",

          text: data.message || "Descuento registrado correctamente",

          icon: "success",

          confirmButtonText: "Aceptar",

          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          window.location.reload(true);
        });
      } else {
        Swal.fire({
          title: "Error",

          text: data.message || "Ocurrió un error al registrar",

          icon: "error",

          confirmButtonText: "Aceptar",

          customClass: {
            confirmButton: "classbotones",
          },
        });
      }
    } catch (error) {
      console.error(error);

      Swal.fire({
        title: "Error",

        text: "Error de conexión o inesperado",

        icon: "error",

        confirmButtonText: "Aceptar",

        customClass: {
          confirmButton: "classbotones",
        },
      });
    }
  });
});
// =========================
// LLENAR FORMULARIO
// =========================
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-edit").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.getAttribute("data-id");

      try {
        const response = await fetch(`/manager/descuentos/get/${id}/`);
        const data = await response.json();

        if (!data.success) {
          Swal.fire("Error", data.message, "error");
          return;
        }

        const d = data.descuento;

        // =========================
        // GENERALES
        // =========================
        document.getElementById("idedit").value = d.id;
        document.getElementById("nombreedit").value = d.nombre;
        document.getElementById("descripcionedit").value = d.descripcion || "";

        // =========================
        // CUPÓN
        // =========================
        const esCupon = document.getElementById("es_cuponedit");
        const divCodigo = document.getElementById("divcodigoedit");

        esCupon.checked = d.es_cupon;
        document.getElementById("codigoedit").value = d.codigo || "";

        divCodigo.style.display = d.es_cupon ? "block" : "none";
        if (esCupon) esCupon.dispatchEvent(new Event("change"));

        // =========================
        // TIPO
        // =========================
        document.getElementById("es_porcentajeedit").checked = d.es_porcentaje;
        document.getElementById("valoredit").value = d.valor || "";

        document.getElementById("acumulableedit").checked = d.acumulable;
        document.getElementById("is_activeedit").checked = d.is_active;

        // =========================
        // CANTIDAD (FIX IMPORTANTE)
        // =========================
        const esCantidad = document.getElementById("es_cantidadedit");
        const contCantidad = document.getElementById("contenedor_cantidadedit");

        const inputLleva = document.getElementById("cantidad_llevaedit");
        const inputPaga = document.getElementById("cantidad_pagaedit");

        esCantidad.checked = d.es_cantidad;
        inputLleva.value = d.es_cantidad ? d.cantidad_lleva || "" : "";
        inputPaga.value = d.es_cantidad ? d.cantidad_paga || "" : "";
        if (esCantidad) esCantidad.dispatchEvent(new Event("change"));

        // =========================
        // APLICACIÓN
        // =========================
        const aplicarProd = document.getElementById("aplicar_productosedit");
        const aplicarCat = document.getElementById("aplicar_categoriasedit");

        const contProd = document.getElementById("contenedor_productosedit");
        const contCat = document.getElementById("contenedor_categoriasedit");

        aplicarProd.checked = d.aplicar_productos;
        aplicarCat.checked = d.aplicar_categorias;
        toggleAplicarProductosEdit(aplicarProd.checked);
        toggleAplicarCategoriasEdit(aplicarCat.checked);

        // PRODUCTO
        if (d.aplicar_productos) {
          contProd.style.display = "block";
          document.getElementById("productoidedit").value = d.productoid || "";

          const btn = contProd.querySelector("button");
          if (btn) btn.textContent = d.productonombre || "Seleccionar producto";
        } else {
          contProd.style.display = "none";
        }

        // CATEGORÍA
        if (d.aplicar_categorias) {
          contCat.style.display = "block";
          document.getElementById("categoriaidedit").value =
            d.categoriaid || "";

          const btn = contCat.querySelector("button");
          if (btn)
            btn.textContent = d.categorianombre || "Seleccionar categoría";
        } else {
          contCat.style.display = "none";
        }

        // =========================
        // LIMITES
        // =========================
        document.getElementById("limite_usoedit").value = d.limite_uso || "";
        document.getElementById("fecha_inicioedit").value =
          d.fecha_inicio || "";
        document.getElementById("fecha_finedit").value = d.fecha_fin || "";
      } catch (error) {
        console.error(error);
        Swal.fire("Error", "Error al obtener información", "error");
      }
    });
  });
});

//=========================
// PUT DESCUENTO
//=========================
document.addEventListener("DOMContentLoaded", () => {
  const formPut = document.getElementById("putregistro");

  formPut.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("idedit").value;

    const payload = {
      // =========================
      // GENERAL
      // =========================
      nombre: document.getElementById("nombreedit").value,
      descripcion: document.getElementById("descripcionedit").value,

      // =========================
      // CUPON
      // =========================
      es_cupon: document.getElementById("es_cuponedit").checked,
      codigo: document.getElementById("codigoedit").value,

      // =========================
      // TIPO DESCUENTO
      // =========================
      es_porcentaje: document.getElementById("es_porcentajeedit").checked,
      valor: document.getElementById("valoredit").value,

      // =========================
      // CANTIDAD
      // =========================
      es_cantidad: document.getElementById("es_cantidadedit").checked,
      cantidad_lleva: document.getElementById("cantidad_llevaedit").value,
      cantidad_paga: document.getElementById("cantidad_pagaedit").value,

      // =========================
      // APLICACION
      // =========================
      aplicar_productos: document.getElementById("aplicar_productosedit")
        .checked,
      aplicar_categorias: document.getElementById("aplicar_categoriasedit")
        .checked,
      productoid: document.getElementById("productoidedit").value,
      categoriaid: document.getElementById("categoriaidedit").value,

      // =========================
      // LIMITES
      // =========================
      limite_uso: document.getElementById("limite_usoedit").value,

      // =========================
      // FECHAS
      // =========================
      fecha_inicio: document.getElementById("fecha_inicioedit").value,
      fecha_fin: document.getElementById("fecha_finedit").value,

      // =========================
      // CONFIG
      // =========================
      acumulable: document.getElementById("acumulableedit").checked,
      is_active: document.getElementById("is_activeedit").checked,
    };

    try {
      const response = await fetch(`/manager/descuentos/put/${id}/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
        const modal = bootstrap.Modal.getInstance(
          document.getElementById("modalput"),
        );

        modal.hide();

        Swal.fire({
          title: "¡Éxito!",
          text: data.message || "Actualizado correctamente",
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          window.location.reload(true);
        });
      } else {
        Swal.fire({
          title: "Error",
          text: data.message || "Error al actualizar",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        });
      }
    } catch (error) {
      console.error(error);

      Swal.fire({
        title: "Error",
        text: "Error de conexión o inesperado",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
    }
  });
});
