//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("postregistro");
  const modalElement = document.getElementById("modalregis");
  const modal = new bootstrap.Modal(modalElement);

  const imagenInput = document.getElementById("imagenproducto");

  function convertImageToWebP(file, quality = 0.8) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = function (event) {
        const img = new Image();

        img.onload = function () {
          const canvas = document.createElement("canvas");
          canvas.width = img.width;
          canvas.height = img.height;

          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0);

          canvas.toBlob(
            (blob) => {
              if (!blob) return reject(new Error("Error conversión"));

              const webpFile = new File(
                [blob],
                file.name.replace(/\.[^/.]+$/, ".webp"),
                { type: "image/webp" },
              );

              resolve(webpFile);
            },
            "image/webp",
            quality,
          );
        };

        img.onerror = reject;
        img.src = event.target.result;
      };

      reader.readAsDataURL(file);
    });
  }

  // =====================
  // SUBMIT
  // =====================
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData();

    // =====================
    // DATOS
    // =====================
    formData.append("nombre", document.getElementById("Nombre").value);
    formData.append(
      "descripcion",
      document.getElementById("Descripcion").value,
    );
    formData.append("categoria", document.getElementById("CategoriaId").value);
    formData.append(
      "unidad_medida",
      document.getElementById("UnidadMedidaId").value,
    );
    formData.append("marca", document.getElementById("MarcaId").value);
    formData.append("codigo_sku", document.getElementById("CodigoSKU").value);
    formData.append(
      "precio_venta",
      document.getElementById("precioVenta").value,
    );

    const vencimientoCheckbox = document.getElementById("vencimiento");
    formData.append("Vencimiento", vencimientoCheckbox.checked);

    // =====================
    // VALIDACIÓN IMÁGENES (USANDO ARRAY REAL)
    // =====================
    if (!imagenes || imagenes.length === 0) {
      Swal.fire({
        title: "Imágenes requeridas",
        text: "Debes agregar al menos una imagen",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
      return;
    }

    if (imagenes.length > 5) {
      Swal.fire({
        title: "Límite excedido",
        text: "Solo puedes subir máximo 5 imágenes",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
      return;
    }

    // =====================
    // CONVERTIR Y ENVIAR
    // =====================
    for (let file of imagenes) {
      const ext = file.name.split(".").pop().toLowerCase();

      if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
        Swal.fire({
          title: "Formato inválido",
          text: "Solo JPG, PNG o WEBP",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        });
        return;
      }

      try {
        const webpFile = await convertImageToWebP(file);

        // nombre original opcional
        webpFile.originalName = file.name.replace(/\.[^/.]+$/, "");

        formData.append("Imagenes", webpFile);
      } catch (error) {
        Swal.fire({
          title: "Error",
          text: "No se pudo procesar una imagen",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        });
        return;
      }
    }

    // =====================
    // REQUEST
    // =====================
    try {
      const response = await fetch("/manager/productos/post/", {
        method: "POST",
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        modal.hide();
        form.reset();

        imagenes = [];
        document.querySelectorAll(".imagen-box").forEach((el) => {
          if (!el.classList.contains("add-image")) el.remove();
        });

        Swal.fire({
          title: "¡Éxito!",
          text: data.message,
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => location.reload());
      } else {
        Swal.fire({
          title: "Error",
          text: data.message,
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
        text: "Error inesperado",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
    }
  });
});

//----------------
// LLENAR FORMULARIO
//----------------
const inputImagenEdit = document.getElementById("imagenproductoedit");
const containerEdit = document.getElementById("imagenesContainerEdit");
const addButtonEdit = document.getElementById("addImageBtnEdit");

let imagenesEdit = [];
let imagenesEliminar = [];

// =========================
// RENDER IMAGEN
// =========================
function renderImagenEdit(url, id = null, nueva = false) {
  const box = document.createElement("div");

  box.classList.add("imagen-box");

  box.innerHTML = `
    <img src="${url}">

    <button type="button" class="delete-image">
      <i class="bx bx-trash"></i>
    </button>
  `;

  // =========================
  // ELIMINAR
  // =========================
  box.querySelector(".delete-image").addEventListener("click", function () {
    // eliminar visual
    box.remove();

    // =====================
    // IMAGEN EXISTENTE
    // =====================
    if (!nueva && id) {
      imagenesEliminar.push(id);

      imagenesEdit = imagenesEdit.filter((img) => img.id !== id);
    }

    // =====================
    // IMAGEN NUEVA
    // =====================
    if (nueva) {
      imagenesEdit = imagenesEdit.filter((img) => img.file !== nueva);
    }

    // mostrar botón "+"
    if (imagenesEdit.length < 5) {
      addButtonEdit.style.display = "flex";
    }
  });

  containerEdit.insertBefore(box, addButtonEdit);

  // ocultar "+"
  if (imagenesEdit.length >= 5) {
    addButtonEdit.style.display = "none";
  }
}

// =========================
// CLICK +
// =========================
addButtonEdit.addEventListener("click", function (e) {
  e.preventDefault();
  inputImagenEdit.click();
});
// =========================
// AGREGAR NUEVAS
// =========================
inputImagenEdit.addEventListener("change", function (e) {
  const archivos = Array.from(e.target.files || []);

  archivos.forEach((file) => {
    if (imagenesEdit.length >= 5) return;

    imagenesEdit.push({
      file: file,
      nueva: true,
    });

    renderImagenEdit(URL.createObjectURL(file), null, true);
  });

  e.target.value = "";
});

// =========================
// CARGAR EDIT
// =========================
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-edit").forEach((button) => {
    button.addEventListener("click", async () => {
      const Id = button.getAttribute("data-id");

      const response = await fetch(`/manager/productos/get/${Id}/`);

      const data = await response.json();

      if (!data.success) {
        Swal.fire(
          "Error",
          data.message || "No se pudo obtener la información",
          "error",
        );

        return;
      }

      const producto = data.producto;

      // =========================
      // LIMPIAR
      // =========================
      imagenesEdit = [];
      imagenesEliminar = [];

      containerEdit
        .querySelectorAll(".imagen-box:not(.add-image)")
        .forEach((el) => el.remove());

      addButtonEdit.style.display = "flex";

      // =========================
      // CAMPOS
      // =========================
      document.getElementById("idedit").value = producto.id;

      document.getElementById("Nombreedit").value = producto.nombre;

      document.getElementById("Descripcionedit").value = producto.descripcion;

      document.getElementById("CodigoSKUedit").value = producto.codigoSKU;

      document.getElementById("precioVentaedit").value = producto.precioVenta;

      // =========================
      // CATEGORÍA
      // =========================
      setRemoteSelectEdit({
        hiddenId: "CategoriaIdedit",
        value: producto.categoriaId,
        text: producto.categoria?.nombre,
        placeholder: "Categoría",
      });

      // =========================
      // UNIDAD MEDIDA
      // =========================
      setRemoteSelectEdit({
        hiddenId: "UnidadMedidaIdedit",
        value: producto.unidadMedidaId,
        text: producto.unidadMedida
          ? `${producto.unidadMedida.nombre} | ${producto.unidadMedida.abreviatura}`
          : "",
        placeholder: "Presentación",
      });

      // =========================
      // MARCA
      // =========================
      setRemoteSelectEdit({
        hiddenId: "MarcaIdedit",
        value: producto.marcasId,
        text: producto.marcas?.nombre,
        placeholder: "Marca",
      });

      // =========================
      // ESTADO
      // =========================
      const activeCheckbox = document.getElementById("isActiveedit");

      const activeText = document.getElementById("activeTextedit");

      activeCheckbox.checked = producto.isActive;

      activeText.textContent = producto.isActive ? "Activo" : "Inactivo";

      activeText.classList.toggle("text-success", producto.isActive);

      activeText.classList.toggle("text-danger", !producto.isActive);

      // =========================
      // VENCIMIENTO
      // =========================
      const vencimientoCheckbox = document.getElementById("vencimientoedit");

      const vencimientoText = document.getElementById("vencimientoTextedit");

      vencimientoCheckbox.checked = producto.vencimiento;

      vencimientoText.textContent = producto.vencimiento ? "SI" : "NO";

      vencimientoText.classList.toggle("text-success", producto.vencimiento);

      vencimientoText.classList.toggle("text-danger", !producto.vencimiento);

      // =========================
      // IMÁGENES EXISTENTES
      // =========================
      if (producto.imagenes) {
        producto.imagenes.forEach((img) => {
          imagenesEdit.push({
            id: img.id,
            url: img.url,
            nueva: false,
          });

          renderImagenEdit(img.url, img.id, false);
        });
      }
    });
  });
});

function setRemoteSelectEdit({ hiddenId, value, text, placeholder }) {
  const hiddenInput = document.getElementById(hiddenId);
  const dropdownBtn = document.querySelector(
    `#${hiddenId} ~ .select-container button`,
  );
  const optionsContainer = document.querySelector(
    `#${hiddenId} ~ .select-container .options`,
  );

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

  // =========================
  // VALIDACIONES
  // =========================
  const requiredFields = [
    { id: "Nombreedit", name: "Nombre" },
    { id: "Descripcionedit", name: "Descripción" },
    { id: "CategoriaIdedit", name: "Categoría" },
    { id: "UnidadMedidaIdedit", name: "Presentación" },
    { id: "MarcaIdedit", name: "Marca" },
    { id: "CodigoSKUedit", name: "Código de Barras" },
    { id: "precioVentaedit", name: "Precio de Venta" },
  ];

  let missingFields = [];

  requiredFields.forEach((field) => {
    const input = document.getElementById(field.id);

    if (!input.value || input.value.trim() === "") {
      missingFields.push(field.name);
    }
  });

  if (missingFields.length > 0) {
    Swal.fire({
      title: "Campos incompletos",
      text:
        "Por favor completa los siguientes campos: " + missingFields.join(", "),
      icon: "warning",
    });
    return;
  }

  // =========================
  // MÍNIMO 1 IMAGEN
  // =========================
  const imagenesRestantes = imagenesEdit.filter(
    (img) => !imagenesEliminar.includes(img.id),
  );

  if (imagenesRestantes.length === 0) {
    Swal.fire({
      title: "Imágenes requeridas",
      text: "Debes dejar al menos una imagen",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
    return;
  }

  // =========================
  // CONVERTIDOR WEBP
  // =========================
  function convertImageToWebP(file, quality = 0.8) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = function (event) {
        const img = new Image();

        img.onload = function () {
          const canvas = document.createElement("canvas");

          canvas.width = img.width;
          canvas.height = img.height;

          const ctx = canvas.getContext("2d");

          ctx.drawImage(img, 0, 0);

          canvas.toBlob(
            (blob) => {
              if (blob) {
                const webpFile = new File(
                  [blob],
                  file.name.replace(/\.[^/.]+$/, ".webp"),
                  {
                    type: "image/webp",
                  },
                );

                resolve(webpFile);
              } else {
                reject(new Error("No se pudo convertir"));
              }
            },
            "image/webp",
            quality,
          );
        };

        img.onerror = reject;
        img.src = event.target.result;
      };

      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  // =========================
  // FORMDATA
  // =========================
  const formData = new FormData();

  formData.append("Nombre", document.getElementById("Nombreedit").value);

  formData.append(
    "Descripcion",
    document.getElementById("Descripcionedit").value,
  );

  formData.append(
    "CategoriaId",
    document.getElementById("CategoriaIdedit").value,
  );

  formData.append(
    "UnidadMedidaId",
    document.getElementById("UnidadMedidaIdedit").value,
  );

  formData.append("MarcaId", document.getElementById("MarcaIdedit").value);

  formData.append("CodigoSKU", document.getElementById("CodigoSKUedit").value);

  formData.append(
    "precioVenta",
    document.getElementById("precioVentaedit").value,
  );

  formData.append("IsActive", document.getElementById("isActiveedit").checked);

  formData.append(
    "Vencimiento",
    document.getElementById("vencimientoedit").checked,
  );

  // =========================
  // IMÁGENES A ELIMINAR
  // =========================
  imagenesEliminar.forEach((id) => {
    formData.append("ImagenesEliminar[]", id);
  });

  // =========================
  // NUEVAS IMÁGENES
  // =========================
  for (const img of imagenesEdit) {
    if (!img.nueva) continue;

    const file = img.file;

    const ext = file.name.split(".").pop().toLowerCase();

    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      Swal.fire({
        title: "Formato inválido",
        text: "Solo JPG, PNG o WEBP",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });

      return;
    }

    try {
      const webpFile = await convertImageToWebP(file);

      formData.append("Imagenes", webpFile);
    } catch (error) {
      Swal.fire({
        title: "Error",
        text: "No se pudo procesar una imagen",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });

      return;
    }
  }

  // =========================
  // FETCH
  // =========================
  try {
    const response = await fetch(`/manager/productos/put/${Id}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
        "X-HTTP-Method-Override": "PUT",
      },
      body: formData,
    });

    const data = await response.json();

    if (data.success) {
      Swal.fire({
        title: "¡Éxito!",
        text: data.message,
        icon: "success",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      }).then(() => {
        window.location.reload();
      });
    } else {
      Swal.fire({
        title: "Error",
        text: data.message,
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  } catch (error) {
    console.error(error);

    Swal.fire({
      title: "Error",
      text: "Error inesperado",
      icon: "error",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
  }
});
//----------------------
// ELIMINACION
//----------------------
document.addEventListener("DOMContentLoaded", () => {
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

      if (result.isConfirmed) {
        try {
          const response = await fetch(`/manager/productos/delete/${userId}/`, {
            method: "DELETE",
            headers: {
              "X-CSRFToken": document.querySelector(
                "[name=csrfmiddlewaretoken]",
              ).value,
            },
          });

          const data = await response.json();

          if (data.success) {
            // Eliminar fila de la tabla sin recargar
            Swal.fire({
              title: "Eliminado",
              text: data.message,
              icon: "success",
              confirmButtonText: "Aceptar",
              customClass: { confirmButton: "classbotones" },
            }).then(() => {
              window.location.reload(true);
            });
          } else {
            Swal.fire({
              title: "Error",
              text: data.message || "No se pudo eliminar el usuario",
              icon: "error",
              confirmButtonText: "Aceptar",
              customClass: { confirmButton: "classbotones" },
            });
          }
        } catch (error) {
          Swal.fire({
            title: "Error",
            text: "Error de conexión o inesperado. Ver consola para más detalles.",
            icon: "error",
            confirmButtonText: "Aceptar",
            customClass: { confirmButton: "classbotones" },
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
    const res = await fetch(
      `/manager/categorias/search/?search=${encodeURIComponent(term)}`,
    );
    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (data.length === 0) {
      optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">Sin resultados</div>`;
      return;
    }

    data.forEach((c) => {
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

  const res = await fetch(
    `/manager/presentaciones/search/?search=${encodeURIComponent(term)}`,
  );
  const data = await res.json();

  optionsContainer.innerHTML = "";

  if (data.length === 0) {
    optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">Sin resultados</div>`;
    return;
  }

  data.forEach((u) => {
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

  const res = await fetch(
    `/manager/marcas/search/?search=${encodeURIComponent(term)}`,
  );
  const data = await res.json();

  optionsContainer.innerHTML = "";

  if (data.length === 0) {
    optionsContainer.innerHTML = `
            <div class="list-group-item text-muted">Sin resultados</div>`;
    return;
  }

  data.forEach((m) => {
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
  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        remoteSearchFn(searchInput.value.trim(), optionsContainer);
      }
    }, 300),
  );

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
initDropdown("UnidadMedidaId", fetchUMedidas); // Otros sin búsqueda remota
initDropdown("MarcaId", fetchMarcas);
initDropdown("CategoriaIdedit", fetchCategorias);
initDropdown("UnidadMedidaIdedit", fetchUMedidas);
initDropdown("MarcaIdedit", fetchMarcas);

document.addEventListener("DOMContentLoaded", () => {
  const vencimientoCheckbox = document.getElementById("vencimiento");
  const vencimientoText = document.getElementById("vencimientoText");

  if (vencimientoCheckbox && vencimientoText) {
    const toggleVencimientoText = () => {
      if (vencimientoCheckbox.checked) {
        vencimientoText.textContent = "Si";
        vencimientoText.classList.remove("text-danger");
        vencimientoText.classList.add("text-success");
      } else {
        vencimientoText.textContent = "No";
        vencimientoText.classList.remove("text-success");
        vencimientoText.classList.add("text-danger");
      }
    };

    toggleVencimientoText(); // Inicializa el texto
    vencimientoCheckbox.addEventListener("change", toggleVencimientoText);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const vencimientoCheckbox = document.getElementById("vencimientoedit");
  const vencimientoText = document.getElementById("vencimientoTextedit");

  if (vencimientoCheckbox && vencimientoText) {
    const toggleVencimientoText = () => {
      if (vencimientoCheckbox.checked) {
        vencimientoText.textContent = "Si";
        vencimientoText.classList.remove("text-danger");
        vencimientoText.classList.add("text-success");
      } else {
        vencimientoText.textContent = "No";
        vencimientoText.classList.remove("text-success");
        vencimientoText.classList.add("text-danger");
      }
    };

    toggleVencimientoText(); // Inicializa el texto
    vencimientoCheckbox.addEventListener("change", toggleVencimientoText);
  }
});

//----------------IMAGENES PRODUCTOS----------------
const inputImagen = document.getElementById("imagenproducto");
const container = document.getElementById("imagenesContainer");
const addButton = document.getElementById("addImageBtn");

let imagenes = [];

// =====================
// CLICK "+"
// =====================
addButton.addEventListener("click", function (e) {
  e.preventDefault();
  e.stopPropagation();
  inputImagen.click();
});

// =====================
// CHANGE INPUT
// =====================
inputImagen.addEventListener("change", function (e) {
  const archivos = Array.from(e.target.files || []);

  console.log("FILES REAL:", archivos);

  if (archivos.length === 0) return;

  archivos.forEach((file) => {
    if (imagenes.length >= 5) return;

    imagenes.push(file);

    const reader = new FileReader();

    reader.onload = function (event) {
      const box = document.createElement("div");
      box.classList.add("imagen-box");

      box.innerHTML = `
        <img src="${event.target.result}">
        <button type="button" class="delete-image"><i class="bx bx-trash"></i></button>
      `;

      box.querySelector(".delete-image").addEventListener("click", function () {
        const index = imagenes.indexOf(file);
        if (index !== -1) imagenes.splice(index, 1);

        box.remove();

        if (imagenes.length < 5) {
          addButton.style.display = "flex";
        }
      });

      container.appendChild(box);
    };

    reader.readAsDataURL(file);
  });

  e.target.value = "";
});

document.querySelectorAll(".img-hover-wrapper").forEach((el) => {
  const popup = el.querySelector(".img-hover-popup");

  el.addEventListener("mouseenter", (e) => {
    popup.classList.add("show");
  });

  el.addEventListener("mousemove", (e) => {
    popup.style.left = e.pageX + 15 + "px";
    popup.style.top = e.pageY + 15 + "px";
  });

  el.addEventListener("mouseleave", () => {
    popup.classList.remove("show");
  });
});
