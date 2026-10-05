//----------------
// VALIDAR NUMERO EN INPUT
//----------------
function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, '');
}

const DEFAULT_PRODUCT_IMAGE = "/static/img/default.webp";

function setSubmitButtonState(button, isProcessing) {
  button.disabled = isProcessing;
  button.textContent = isProcessing ? "Procesando..." : "Guardar";
}

//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("postregistro");
  const modalElement = document.getElementById("modalregis");
  const modal = new bootstrap.Modal(modalElement);
  const submitButton = document.getElementById("btnregis");
  let enviandoRegistro = false;

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

    if (enviandoRegistro) return;

    const precioVenta = Number(document.getElementById("precioVenta").value);
    const precioMinTexto = document.getElementById("precioVentaMin").value.trim();
    const precioMaxTexto = document.getElementById("precioVentaMax").value.trim();
    const precioMin = precioMinTexto === "" ? null : Number(precioMinTexto);
    const precioMax = precioMaxTexto === "" ? null : Number(precioMaxTexto);

    if (!Number.isFinite(precioVenta) || precioVenta < 0 || (precioMin !== null && (!Number.isFinite(precioMin) || precioMin < 0)) || (precioMax !== null && (!Number.isFinite(precioMax) || precioMax < 0)) || (precioMin !== null && precioMax !== null && precioMax < precioMin)) {
      Swal.fire({
        title: "Rango de precios inválido",
        text: "El precio máximo debe ser mayor o igual al precio mínimo.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

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
    formData.append("precio_venta", document.getElementById("precioVenta").value);
    formData.append("precio_venta_min", document.getElementById("precioVentaMin").value);
    formData.append("precio_venta_max", document.getElementById("precioVentaMax").value);

    formData.append("impuesto", document.getElementById("impuesto").value);
    const vencimientoCheckbox = document.getElementById("vencimiento");
    formData.append("Vencimiento", vencimientoCheckbox.checked);
    const espadreCheckbox = document.getElementById("espadre");
    formData.append("Espadre", espadreCheckbox.checked)
    formData.append(
        "vunid",
        parseFloat(document.getElementById("vunid").value)
    );

    // =====================
    // VALIDACIÓN IMÁGENES (USANDO ARRAY REAL)
    // =====================
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

    enviandoRegistro = true;
    setSubmitButtonState(submitButton, true);
    // La conversión de imágenes sucede antes del fetch; mostramos el loader
    // desde el clic válido y no hasta que la petición HTTP inicia.
    window.managerLoader?.mostrar();
    let loaderRegistroActivo = Boolean(window.managerLoader);

    const finalizarRegistro = () => {
      enviandoRegistro = false;
      setSubmitButtonState(submitButton, false);
      if (loaderRegistroActivo) {
        window.managerLoader?.ocultar();
        loaderRegistroActivo = false;
      }
    };

    // =====================
    // CONVERTIR Y ENVIAR
    // =====================
    for (let file of imagenes) {
      const ext = file.name.split(".").pop().toLowerCase();

      if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
        finalizarRegistro();
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
        finalizarRegistro();
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
        finalizarRegistro();
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
        finalizarRegistro();
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
      finalizarRegistro();
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

  const imagenVistaPrevia = box.querySelector("img");
  imagenVistaPrevia.addEventListener("error", function () {
    this.onerror = null;
    this.src = DEFAULT_PRODUCT_IMAGE;
  });

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
// LLENAR FORMULARIO
// =========================
document.addEventListener("DOMContentLoaded", () => {
  const modalEditar = document.getElementById("modalput");

  modalEditar.addEventListener("show.bs.modal", async (event) => {
      const button = event.relatedTarget;
      const Id = button?.getAttribute("data-id");

      if (!Id) return;

      try {
        const response = await fetch(`/manager/productos/get/${Id}/`);

        if (!response.ok) {
          throw new Error("No se pudo obtener el producto");
        }

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
      document.getElementById("precioVentaMinedit").value = producto.precioVentaMin ?? "";
      document.getElementById("precioVentaMaxedit").value = producto.precioVentaMax ?? "";

      document.getElementById("impuestoedit").value = producto.impuesto;

      document.getElementById("vunidedit").value = producto.equival_unid;

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

      const esPadreCheckbox = document.getElementById("espadreedit");
      const esPadreText = document.getElementById("espadreTextedit");

      esPadreCheckbox.checked = producto.is_master;

      esPadreText.textContent = producto.is_master ? "Sí" : "No";

      esPadreText.classList.toggle("text-success", producto.is_master);

      esPadreText.classList.toggle("text-danger", !producto.is_master);

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
      } catch (error) {
        console.error(error);
        Swal.fire("Error", "No se pudo cargar la información del producto", "error");
      }
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
let enviandoEdicion = false;

document.getElementById("putregistro").addEventListener("submit", async (e) => {
  e.preventDefault();

  if (enviandoEdicion) return;

  const submitButton = document.getElementById("btnput");

  const Id = document.getElementById("idedit").value;
  const precioVenta = Number(document.getElementById("precioVentaedit").value);
  const precioMinTexto = document.getElementById("precioVentaMinedit").value.trim();
  const precioMaxTexto = document.getElementById("precioVentaMaxedit").value.trim();
  const precioMin = precioMinTexto === "" ? null : Number(precioMinTexto);
  const precioMax = precioMaxTexto === "" ? null : Number(precioMaxTexto);

  if (!Number.isFinite(precioVenta) || precioVenta < 0 || (precioMin !== null && (!Number.isFinite(precioMin) || precioMin < 0)) || (precioMax !== null && (!Number.isFinite(precioMax) || precioMax < 0)) || (precioMin !== null && precioMax !== null && precioMax < precioMin)) {
    Swal.fire({
      title: "Rango de precios inválido",
      text: "El precio máximo debe ser mayor o igual al precio mínimo.",
      icon: "warning",
    });
    return;
  }

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
    { id: "impuestoedit", name: "Impuesto" },
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

  enviandoEdicion = true;
  setSubmitButtonState(submitButton, true);
  // Igual que al registrar, la preparación de fotos puede tardar antes de fetch.
  window.managerLoader?.mostrar();
  let loaderEdicionActivo = Boolean(window.managerLoader);

  const finalizarEdicion = () => {
    enviandoEdicion = false;
    setSubmitButtonState(submitButton, false);
    if (loaderEdicionActivo) {
      window.managerLoader?.ocultar();
      loaderEdicionActivo = false;
    }
  };

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

  formData.append("precioVenta", document.getElementById("precioVentaedit").value);
  formData.append("precioVentaMin", document.getElementById("precioVentaMinedit").value);
  formData.append("precioVentaMax", document.getElementById("precioVentaMaxedit").value);
  formData.append("impuesto", document.getElementById("impuestoedit").value);
  formData.append("IsActive", document.getElementById("isActiveedit").checked);

  formData.append(
    "Vencimiento",
    document.getElementById("vencimientoedit").checked,
  );

  formData.append("Espadre", document.getElementById("espadreedit").checked);

  formData.append("vunid", parseFloat(document.getElementById("vunidedit").value));

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
      finalizarEdicion();
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
      finalizarEdicion();
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
      finalizarEdicion();
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
      finalizarEdicion();
      Swal.fire({
        title: "Error",
        text: data.message,
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  } catch (error) {
    finalizarEdicion();
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

    optionsContainer.innerHTML = `
        <div class="list-group-item active bg-light text-dark fw-bold">
            ${term ? "Resultados encontrados" : "Más utilizadas"}
        </div>`;

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

  optionsContainer.innerHTML = `
        <div class="list-group-item active bg-light text-dark fw-bold">
            ${term ? "Resultados encontrados" : "Más utilizadas"}
        </div>`;

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

  optionsContainer.innerHTML = `
        <div class="list-group-item active bg-light text-dark fw-bold">
            ${term ? "Resultados encontrados" : "Más utilizadas"}
        </div>`;

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
  const placeholderText = selectBtn.textContent.trim();

  // Selección de opción
  optionsContainer.addEventListener("click", (e) => {
    const option = e.target.closest(".list-group-item-action");

    if (!option) return;

    hiddenInput.value = option.dataset.value;
    selectBtn.textContent = option.textContent.trim();
    dropdown.classList.remove("show");
    searchInput.value = "";
  });

  // Abrir/ocultar dropdown
  selectBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const estabaAbierto = dropdown.classList.contains("show");

    // Los tres selectores están uno debajo del otro: al abrir uno se cierran
    // los demás para evitar que sus listas se superpongan.
    document
      .querySelectorAll(".gestion-producto-select .dropdown-menu.show")
      .forEach((menu) => menu.classList.remove("show"));

    dropdown.classList.toggle("show", !estabaAbierto);
    searchInput.focus();

    if (remoteSearchFn && dropdown.classList.contains("show")) {
      remoteSearchFn(searchInput.value.trim(), optionsContainer);
    }
  });

  // Buscar mientras escribe (solo si tiene función remota)
  searchInput.addEventListener(
    "input",
    debounce(() => {
      if (remoteSearchFn) {
        const term = searchInput.value.trim();

        remoteSearchFn(term, optionsContainer);
      }
    }, 300),
  );

  searchInput.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;

    e.preventDefault();

    const firstOption = optionsContainer.querySelector(
      ".list-group-item-action:not(.text-muted)",
    );

    if (firstOption) {
      firstOption.click();
    }
  });

  // Cerrar dropdown al hacer click fuera
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".select-container")) {
      dropdown.classList.remove("show");
    }
  });

  if (hiddenInput.value) {
    selectBtn.textContent = placeholderText;
  }

  return { hiddenInput, selectBtn, optionsContainer };
}



//----------------CHECKBOX----------------

document.addEventListener("DOMContentLoaded", () => {
    const espadreCheckbox = document.getElementById("espadre");
    const espadreCheckboxText = document.getElementById("espadreText");

    if (espadreCheckbox && espadreCheckboxText) {

        const toggleEsPadreText = () => {
            if (espadreCheckbox.checked) {
                espadreCheckboxText.textContent = "SI";

                espadreCheckboxText.classList.remove("text-danger");
                espadreCheckboxText.classList.add("text-success");
            } else {
                espadreCheckboxText.textContent = "NO";

                espadreCheckboxText.classList.remove("text-success");
                espadreCheckboxText.classList.add("text-danger");
            }
        };

        // Estado inicial
        toggleEsPadreText();

        // Cuando cambia el checkbox
        espadreCheckbox.addEventListener(
            "change",
            toggleEsPadreText
        );
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const espadreCheckboxedit = document.getElementById("espadreedit");
    const espadreCheckboxTextedit = document.getElementById("espadreTextedit");

    if (espadreCheckboxedit && espadreCheckboxTextedit) {

        const toggleEsPadreText = () => {
            if (espadreCheckboxedit.checked) {
                espadreCheckboxTextedit.textContent = "SI";

                espadreCheckboxTextedit.classList.remove("text-danger");
                espadreCheckboxTextedit.classList.add("text-success");
            } else {
                espadreCheckboxTextedit.textContent = "NO";

                espadreCheckboxTextedit.classList.remove("text-success");
                espadreCheckboxTextedit.classList.add("text-danger");
            }
        };

        // Estado inicial
        toggleEsPadreText();

        // Cuando cambia el checkbox
        espadreCheckboxedit.addEventListener(
            "change",
            toggleEsPadreText
        );
    }
});



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

document.addEventListener("DOMContentLoaded", () => {
  const boton = document.getElementById("exportarProductosExcel");
  if (!boton) return;

  const icono = boton.querySelector("i");
  const iconoOriginal = "bx bx-spreadsheet";

  boton.addEventListener("click", async () => {
    const busqueda = document.getElementById("busqueda")?.value || "";
    const parametros = new URLSearchParams({ search: busqueda });

    boton.disabled = true;
    icono.className = "bx bx-loader-alt bx-spin";
    boton.setAttribute("aria-label", "Generando archivo de Excel");

    try {
      const respuesta = await fetch(
        `${boton.dataset.exportUrl}?${parametros.toString()}`,
      );

      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = "productos.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch (error) {
      Swal.fire("Error", "No se pudo exportar el listado de productos", "error");
    } finally {
      boton.disabled = false;
      icono.className = iconoOriginal;
      boton.setAttribute("aria-label", "Exportar productos a Excel");
    }
  });
});
