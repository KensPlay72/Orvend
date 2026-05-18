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

// Estado inicial

contenedorProductos.style.display = "none";
contenedorProductosEdit.style.display = "none";

contenedorCategorias.style.display = "none";
contenedorCategoriasEdit.style.display = "none";

//----------------
// PRODUCTOS
//----------------

aplicarProductos.addEventListener("change", function () {
  if (this.checked) {
    contenedorProductos.style.display = "block";

    aplicarCategorias.checked = false;

    contenedorCategorias.style.display = "none";

    document.getElementById("categoriaid").value = "";
  } else {
    contenedorProductos.style.display = "none";

    document.getElementById("productoid").value = "";
  }
});

aplicarProductosEdit.addEventListener("change", function () {
  if (this.checked) {
    contenedorProductosEdit.style.display = "block";

    aplicarCategoriasEdit.checked = false;

    contenedorCategoriasEdit.style.display = "none";

    document.getElementById("categoriaidedit").value = "";
  } else {
    contenedorProductosEdit.style.display = "none";

    document.getElementById("productoidedit").value = "";
  }
});

//----------------
// CATEGORIAS
//----------------

aplicarCategorias.addEventListener("change", function () {
  if (this.checked) {
    contenedorCategorias.style.display = "block";

    aplicarProductos.checked = false;

    contenedorProductos.style.display = "none";

    document.getElementById("productoid").value = "";
  } else {
    contenedorCategorias.style.display = "none";

    document.getElementById("categoriaid").value = "";
  }
});

aplicarCategoriasEdit.addEventListener("change", function () {
  if (this.checked) {
    contenedorCategoriasEdit.style.display = "block";

    aplicarProductosEdit.checked = false;

    contenedorProductosEdit.style.display = "none";

    document.getElementById("productoidedit").value = "";
  } else {
    contenedorCategoriasEdit.style.display = "none";

    document.getElementById("categoriaidedit").value = "";
  }
});

//----------------
// CUPONES
//----------------

$("#es_cupon").on("change", function () {
  if ($(this).is(":checked")) {
    $("#divcodigo").show();
  } else {
    $("#divcodigo").hide();

    $("#codigo").val("");
  }
});

$("#es_cuponedit").on("change", function () {
  if ($(this).is(":checked")) {
    $("#divcodigoedit").show();
  } else {
    $("#divcodigoedit").hide();

    $("#codigoedit").val("");
  }
});

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

      requiere_codigo: document.getElementById("requiere_codigo").checked,
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

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-edit").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.getAttribute("data-id");

      try {
        const response = await fetch(`/manager/descuentos/get/${id}/`);

        const data = await response.json();

        if (data.success) {
          const d = data.descuento;

          // =========================
          // GENERALES
          // =========================

          document.getElementById("idedit").value = d.id;

          document.getElementById("nombreedit").value = d.nombre;

          document.getElementById("descripcionedit").value =
            d.descripcion || "";

          // =========================
          // CUPON
          // =========================

          document.getElementById("es_cuponedit").checked = d.es_cupon;

          document.getElementById("codigoedit").value = d.codigo || "";

          // Mostrar/Ocultar código
          if (d.es_cupon) {
            $("#divcodigoedit").show();
          } else {
            $("#divcodigoedit").hide();
          }

          // =========================
          // TIPO
          // =========================

          document.getElementById("es_porcentajeedit").checked =
            d.es_porcentaje;

          document.getElementById("valoredit").value = d.valor;

          // =========================
          // APLICACION
          // =========================

          document.getElementById("aplicar_productosedit").checked =
            d.aplicar_productos;

          document.getElementById("aplicar_categoriasedit").checked =
            d.aplicar_categorias;

          // PRODUCTO
          if (d.aplicar_productos) {
            $("#contenedor_productosedit").show();

            document.getElementById("productoidedit").value = d.productoid;

            document.querySelector(
              "#contenedor_productosedit button",
            ).textContent = d.productonombre;
          } else {
            $("#contenedor_productosedit").hide();
          }

          // CATEGORIA
          if (d.aplicar_categorias) {
            $("#contenedor_categoriasedit").show();

            document.getElementById("categoriaidedit").value = d.categoriaid;

            document.querySelector(
              "#contenedor_categoriasedit button",
            ).textContent = d.categorianombre;
          } else {
            $("#contenedor_categoriasedit").hide();
          }

          // =========================
          // LIMITES
          // =========================

          document.getElementById("limite_usoedit").value = d.limite_uso || "";

          document.getElementById("fecha_inicioedit").value =
            d.fecha_inicio || "";

          document.getElementById("fecha_finedit").value = d.fecha_fin || "";

          // =========================
          // CONFIG
          // =========================

          document.getElementById("acumulableedit").checked = d.acumulable;

          document.getElementById("requiere_codigoedit").checked =
            d.requiere_codigo;

          document.getElementById("is_activeedit").checked = d.is_active;
        } else {
          Swal.fire("Error", data.message, "error");
        }
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
      //=========================
      // INFORMACION GENERAL
      //=========================

      nombre: document.getElementById("nombreedit").value,

      descripcion: document.getElementById("descripcionedit").value,

      //=========================
      // CUPON
      //=========================

      es_cupon: document.getElementById("es_cuponedit").checked,

      codigo: document.getElementById("codigoedit").value,

      //=========================
      // TIPO DESCUENTO
      //=========================

      es_porcentaje: document.getElementById("es_porcentajeedit").checked,

      valor: document.getElementById("valoredit").value,

      //=========================
      // APLICACION
      //=========================

      aplicar_productos: document.getElementById("aplicar_productosedit")
        .checked,

      aplicar_categorias: document.getElementById("aplicar_categoriasedit")
        .checked,

      productoid: document.getElementById("productoidedit").value,

      categoriaid: document.getElementById("categoriaidedit").value,

      //=========================
      // LIMITES
      //=========================

      limite_uso: document.getElementById("limite_usoedit").value,

      //=========================
      // FECHAS
      //=========================

      fecha_inicio: document.getElementById("fecha_inicioedit").value,

      fecha_fin: document.getElementById("fecha_finedit").value,

      //=========================
      // CONFIGURACIONES
      //=========================

      acumulable: document.getElementById("acumulableedit").checked,

      requiere_codigo: document.getElementById("requiere_codigoedit").checked,

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
        const modalElement = document.getElementById("modalput");

        const modal = bootstrap.Modal.getInstance(modalElement);

        modal.hide();

        Swal.fire({
          title: "¡Éxito!",

          text: data.message || "Descuento actualizado correctamente",

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

          text: data.message || "Ocurrió un error al actualizar",

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
