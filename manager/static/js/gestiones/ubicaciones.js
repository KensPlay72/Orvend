//----------------
// VALIDACION SWITCHES
//----------------
document.addEventListener("DOMContentLoaded", () => {
  const bodega = document.getElementById("es_bodega");
  const tienda = document.getElementById("es_tienda");

  // =========================
  // BODEGA
  // =========================
  bodega.addEventListener("change", function () {
    if (this.checked) {
      tienda.checked = false;
    }
  });

  // =========================
  // TIENDA
  // =========================
  tienda.addEventListener("change", function () {
    if (this.checked) {
      bodega.checked = false;
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const bodegaEdit = document.getElementById("es_bodegaedit");
  const tiendaEdit = document.getElementById("es_tiendaedit");

  bodegaEdit.addEventListener("change", function () {
    if (this.checked) {
      tiendaEdit.checked = false;
    }
  });

  tiendaEdit.addEventListener("change", function () {
    if (this.checked) {
      bodegaEdit.checked = false;
    }
  });
});
const MAX_UBICACION_IMAGE_BYTES = 5 * 1024 * 1024;
const UBICACION_IMG_WIDTH = 800;
const UBICACION_IMG_HEIGHT = 600;

const validarMedidasUbicacion = (file) =>
  new Promise((resolve) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({
        valido:
          img.naturalWidth === UBICACION_IMG_WIDTH &&
          img.naturalHeight === UBICACION_IMG_HEIGHT,
        ancho: img.naturalWidth,
        alto: img.naturalHeight,
      });
    };
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({ valido: false, ancho: 0, alto: 0 });
    };
    img.src = objectUrl;
  });

//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("postregistro");
  const modalElement = document.getElementById("modalregis");
  const modal = new bootstrap.Modal(modalElement);
  const inputImagen = document.getElementById("imagen_ubicacion");
  const previewWrap = document.getElementById("preview_imagen_ubicacion_wrap");
  const defaultImagen = document.getElementById("default_imagen_ubicacion");
  const previewImg = document.getElementById("preview_imagen_ubicacion");
  const btnQuitarImagen = document.getElementById("btn_quitar_imagen");

  const limpiarVistaImagenCrear = () => {
    if (inputImagen) inputImagen.value = "";
    if (previewImg) {
      previewImg.src = "";
      previewImg.hidden = true;
    }
    if (btnQuitarImagen) btnQuitarImagen.hidden = true;
    if (defaultImagen) defaultImagen.hidden = false;
  };

  previewWrap?.addEventListener("click", (e) => {
    if (e.target.closest("#btn_quitar_imagen")) return;
    inputImagen?.click();
  });

  previewWrap?.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && !e.target.closest("#btn_quitar_imagen")) {
      e.preventDefault();
      inputImagen?.click();
    }
  });

  inputImagen?.addEventListener("change", async () => {
    const file = inputImagen.files?.[0];
    if (!file) {
      limpiarVistaImagenCrear();
      return;
    }
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      limpiarVistaImagenCrear();
      Swal.fire({
        title: "Formato inválido",
        text: "La imagen de la ubicación debe ser JPG, PNG o WEBP.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    if (file.size > MAX_UBICACION_IMAGE_BYTES) {
      limpiarVistaImagenCrear();
      Swal.fire({
        title: "Imagen demasiado pesada",
        text: "La imagen de la ubicación no debe superar los 5 MB.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const medidas = await validarMedidasUbicacion(file);
    if (!medidas.valido) {
      limpiarVistaImagenCrear();
      Swal.fire({
        title: "Medida incorrecta",
        text: `La imagen de la sucursal debe medir exactamente ${UBICACION_IMG_WIDTH} × ${UBICACION_IMG_HEIGHT} píxeles (ancho: ${UBICACION_IMG_WIDTH}px, alto: ${UBICACION_IMG_HEIGHT}px). La imagen seleccionada mide ${medidas.ancho} × ${medidas.alto} px.`,
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    previewImg.src = URL.createObjectURL(file);
    previewImg.hidden = false;
    if (btnQuitarImagen) btnQuitarImagen.hidden = false;
    if (defaultImagen) defaultImagen.hidden = true;
  });

  btnQuitarImagen?.addEventListener("click", (e) => {
    e.stopPropagation();
    limpiarVistaImagenCrear();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const inputTel = document.getElementById("telefono_ubicacion");
    const valorTel = inputTel ? inputTel.value.trim() : "";

    const formData = new FormData();
    formData.append("nombre", document.getElementById("nubicacion").value.trim());
    formData.append("telefono", valorTel);
    formData.append("Telefono", valorTel);
    formData.append("telefono_ubicacion", valorTel);
    formData.append("pais", document.getElementById("pais_ubicacion")?.value.trim() || "");
    formData.append("departamento", document.getElementById("departamento_ubicacion")?.value.trim() || "");
    formData.append("ubicacion", document.getElementById("nubicaciondeta").value.trim());
    formData.append("es_bodega", String(document.getElementById("es_bodega").checked));
    formData.append("es_tienda", String(document.getElementById("es_tienda").checked));
    formData.append("codigo", document.getElementById("cubicacion").value.trim());
    formData.append(
      "relacion_bodega",
      String(document.getElementById("relacion_bodega")?.checked || false)
    );
    formData.append("bodega_id", document.getElementById("bodegaid").value || "");
    formData.append(
      "horario",
      document.getElementById("horario_ubicacion")?.value.trim() || ""
    );
    formData.append(
      "mapa_iframe",
      document.getElementById("mapa_iframe")?.value.trim() || ""
    );
    formData.append(
      "como_llegar_url",
      document.getElementById("como_llegar_url")?.value.trim() || ""
    );

    const archivoImagen = inputImagen?.files?.[0];
    if (archivoImagen) {
      if (archivoImagen.size > MAX_UBICACION_IMAGE_BYTES) {
        Swal.fire({
          title: "Imagen demasiado pesada",
          text: "La imagen de la ubicación no debe superar los 5 MB.",
          icon: "warning",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }
      const medidas = await validarMedidasUbicacion(archivoImagen);
      if (!medidas.valido) {
        Swal.fire({
          title: "Medida incorrecta",
          text: `La imagen de la sucursal debe medir exactamente ${UBICACION_IMG_WIDTH} × ${UBICACION_IMG_HEIGHT} píxeles.`,
          icon: "warning",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }
      formData.append("imagen", archivoImagen);
    }

    try {
      const response = await fetch("/manager/ubicaciones/post/", {
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

        // reset UI visual
        document.getElementById("bodega_container").hidden = true;
        document.getElementById("switch_relacion").style.display = "none";
        document.getElementById("tienda_extra_container").hidden = true;
        limpiarVistaImagenCrear();

        Swal.fire({
          title: "¡Éxito!",
          text: data.message || "Ubicación registrada correctamente",
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        }).then(() => {
          window.location.reload(true);
        });
      } else {
        Swal.fire({
          title: "Error",
          text: data.message || "Ocurrió un error al registrar",
          icon: "error",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
      }
    } catch (error) {
      console.error(error);

      Swal.fire({
        title: "Error",
        text: "Error de conexión o inesperado",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  });
});
//----------------------
// LLENAR FORMULARIO
//----------------------
document.addEventListener("DOMContentLoaded", () => {
  const inputImagenEdit = document.getElementById("imagen_ubicacionedit");
  const previewWrapEdit = document.getElementById("preview_imagen_ubicacionedit_wrap");
  const defaultImagenEdit = document.getElementById("default_imagen_ubicacionedit");
  const previewImgEdit = document.getElementById("preview_imagen_ubicacionedit");
  const quitarImagenEdit = document.getElementById("quitar_imagenedit");
  const btnQuitarImagenEdit = document.getElementById("btn_quitar_imagenedit");

  const mostrarImagenEdit = (src) => {
    if (previewImgEdit) {
      previewImgEdit.src = src;
      previewImgEdit.hidden = false;
    }
    if (btnQuitarImagenEdit) btnQuitarImagenEdit.hidden = false;
    if (defaultImagenEdit) defaultImagenEdit.hidden = true;
  };

  const ocultarImagenEdit = () => {
    if (previewImgEdit) {
      previewImgEdit.src = "";
      previewImgEdit.hidden = true;
    }
    if (btnQuitarImagenEdit) btnQuitarImagenEdit.hidden = true;
    if (defaultImagenEdit) defaultImagenEdit.hidden = false;
  };

  previewWrapEdit?.addEventListener("click", (e) => {
    if (e.target.closest("#btn_quitar_imagenedit")) return;
    inputImagenEdit?.click();
  });

  previewWrapEdit?.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && !e.target.closest("#btn_quitar_imagenedit")) {
      e.preventDefault();
      inputImagenEdit?.click();
    }
  });

  inputImagenEdit?.addEventListener("change", async () => {
    const file = inputImagenEdit.files?.[0];
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["jpg", "jpeg", "png", "webp"].includes(ext)) {
      inputImagenEdit.value = "";
      Swal.fire({
        title: "Formato inválido",
        text: "La imagen de la ubicación debe ser JPG, PNG o WEBP.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    if (file.size > MAX_UBICACION_IMAGE_BYTES) {
      inputImagenEdit.value = "";
      Swal.fire({
        title: "Imagen demasiado pesada",
        text: "La imagen de la ubicación no debe superar los 5 MB.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const medidas = await validarMedidasUbicacion(file);
    if (!medidas.valido) {
      inputImagenEdit.value = "";
      Swal.fire({
        title: "Medida incorrecta",
        text: `La imagen de la sucursal debe medir exactamente ${UBICACION_IMG_WIDTH} × ${UBICACION_IMG_HEIGHT} píxeles (ancho: ${UBICACION_IMG_WIDTH}px, alto: ${UBICACION_IMG_HEIGHT}px). La imagen seleccionada mide ${medidas.ancho} × ${medidas.alto} px.`,
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    mostrarImagenEdit(URL.createObjectURL(file));
    if (quitarImagenEdit) quitarImagenEdit.value = "false";
  });

  btnQuitarImagenEdit?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (inputImagenEdit) inputImagenEdit.value = "";
    ocultarImagenEdit();
    if (quitarImagenEdit) quitarImagenEdit.value = "true";
  });

  document.querySelectorAll(".btn-edit").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.getAttribute("data-id");

      try {
        const response = await fetch(`/manager/ubicaciones/get/${id}/`);

        const data = await response.json();

        if (!data.success) {
          Swal.fire(
            "Error",
            data.message || "No se pudo obtener la información",
            "error",
          );
          return;
        }

        const ubicacion = data.ubicacion;
        // =========================
        // INPUTS
        // =========================

        document.getElementById("idedit").value = ubicacion.id;

        document.getElementById("nubicacionedit").value =
          ubicacion.nombre || "";

        const inputTelefonoEdit = document.getElementById("telefono_ubicacionedit");
        if (inputTelefonoEdit) inputTelefonoEdit.value = ubicacion.telefono || "";

        const inputPaisEdit = document.getElementById("pais_ubicacionedit");
        if (inputPaisEdit) inputPaisEdit.value = ubicacion.pais || "";

        const inputDeptoEdit = document.getElementById("departamento_ubicacionedit");
        if (inputDeptoEdit) inputDeptoEdit.value = ubicacion.departamento || "";

        document.getElementById("cubicacionedit").value =
          ubicacion.codigo || "";

        document.getElementById("nubicaciondetac").value =
          ubicacion.detalle || "";

        document.getElementById("horario_ubicacionedit").value =
          ubicacion.horario || "";

        document.getElementById("mapa_iframeedit").value =
          ubicacion.mapa_iframe || "";

        document.getElementById("como_llegar_urledit").value =
          ubicacion.como_llegar_url || "";

        if (inputImagenEdit) inputImagenEdit.value = "";
        if (quitarImagenEdit) quitarImagenEdit.value = "false";
        if (ubicacion.imagen_url) {
          mostrarImagenEdit(ubicacion.imagen_url);
        } else {
          ocultarImagenEdit();
        }

        // =========================
        // SWITCHES
        // =========================

        const esBodega = document.getElementById("es_bodegaedit");

        const esTienda = document.getElementById("es_tiendaedit");

        const relacionBodega = document.getElementById("relacion_bodegaedit");

        esBodega.checked = ubicacion.es_bodega;

        esTienda.checked = ubicacion.es_tienda;

        // =========================
        // CONTENEDORES
        // =========================

        const switchRelacion = document.getElementById("switch_relacionedit");

        const bodegaContainer = document.getElementById("bodega_containeredit");
        const tiendaExtraEdit = document.getElementById("tienda_extra_containeredit");

        // =========================
        // MOSTRAR RELACION Y DATOS SI ES TIENDA
        // =========================

        if (ubicacion.es_tienda) {
          switchRelacion.style.display = "block";
          if (tiendaExtraEdit) tiendaExtraEdit.hidden = false;

          // =========================
          // TIENE BODEGA RELACIONADA
          // =========================

          if (ubicacion.bodegaid) {
            relacionBodega.checked = true;

            bodegaContainer.hidden = false;

            document.getElementById("bodegaidedit").value = ubicacion.bodegaid;

            const btnBodega = document.querySelector(
              "#bodega_containeredit button",
            );

            btnBodega.textContent =
              ubicacion.bodeganombre || "Seleccionar bodega";
          } else {
            relacionBodega.checked = false;

            bodegaContainer.hidden = true;

            document.getElementById("bodegaidedit").value = "";

            const btnBodega = document.querySelector(
              "#bodega_containeredit button",
            );

            btnBodega.textContent = "Escriba para buscar...";
          }
        } else {
          switchRelacion.style.display = "none";
          if (tiendaExtraEdit) tiendaExtraEdit.hidden = true;

          relacionBodega.checked = false;

          bodegaContainer.hidden = true;

          document.getElementById("bodegaidedit").value = "";

          const btnBodega = document.querySelector(
            "#bodega_containeredit button",
          );

          btnBodega.textContent = "Escriba para buscar...";
        }

        // =========================
        // ACTIVE
        // =========================

        const isActiveCheckbox = document.getElementById("isActiveedit");

        const activeText = document.getElementById("activeTextedit");

        if (ubicacion.isActive) {
          isActiveCheckbox.checked = true;

          activeText.textContent = "Activo";

          activeText.classList.remove("text-danger");

          activeText.classList.add("text-success");
        } else {
          isActiveCheckbox.checked = false;

          activeText.textContent = "Inactivo";

          activeText.classList.remove("text-success");

          activeText.classList.add("text-danger");
        }
      } catch (error) {
        console.error(error);

        Swal.fire("Error", "Ocurrió un error al cargar la ubicación", "error");
      }
    });
  });
});

//----------------------
// EDICION
//----------------------
document.addEventListener("DOMContentLoaded", () => {
  const formPut = document.getElementById("putregistro");
  if (!formPut) return;

  formPut.addEventListener("submit", async (e) => {
    e.preventDefault();

    const id = document.getElementById("idedit").value;
    const esTienda = document.getElementById("es_tiendaedit").checked;
    const relacionBodega = document.getElementById("relacion_bodegaedit")
      ? document.getElementById("relacion_bodegaedit").checked
      : false;

    const inputTelEdit = document.getElementById("telefono_ubicacionedit");
    const valorTelEdit = inputTelEdit ? inputTelEdit.value.trim() : "";

    const formData = new FormData();
    formData.append("Nombre", document.getElementById("nubicacionedit").value.trim());
    formData.append("nombre", document.getElementById("nubicacionedit").value.trim());
    formData.append("telefono", valorTelEdit);
    formData.append("Telefono", valorTelEdit);
    formData.append("telefono_ubicacionedit", valorTelEdit);
    formData.append("pais", document.getElementById("pais_ubicacionedit")?.value.trim() || "");
    formData.append("departamento", document.getElementById("departamento_ubicacionedit")?.value.trim() || "");
    formData.append("ubicacion", document.getElementById("nubicaciondetac").value.trim());
    formData.append("Codigo", document.getElementById("cubicacionedit").value.trim());
    formData.append("codigo", document.getElementById("cubicacionedit").value.trim());
    formData.append("es_bodega", String(document.getElementById("es_bodegaedit").checked));
    formData.append("es_tienda", String(esTienda));
    formData.append("relacion_bodega", String(relacionBodega));
  formData.append(
    "bodegaid",
    esTienda && relacionBodega ? document.getElementById("bodegaidedit").value || "" : ""
  );
  formData.append("IsActive", String(document.getElementById("isActiveedit").checked));
  formData.append(
    "horario",
    document.getElementById("horario_ubicacionedit")?.value.trim() || ""
  );
  formData.append(
    "mapa_iframe",
    document.getElementById("mapa_iframeedit")?.value.trim() || ""
  );
  formData.append(
    "como_llegar_url",
    document.getElementById("como_llegar_urledit")?.value.trim() || ""
  );
  formData.append(
    "quitar_imagen",
    document.getElementById("quitar_imagenedit")?.value || "false"
  );

  const archivoImagen = document.getElementById("imagen_ubicacionedit")?.files?.[0];
  if (archivoImagen) {
    if (archivoImagen.size > MAX_UBICACION_IMAGE_BYTES) {
      Swal.fire({
        title: "Imagen demasiado pesada",
        text: "La imagen de la ubicación no debe superar los 5 MB.",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    const medidas = await validarMedidasUbicacion(archivoImagen);
    if (!medidas.valido) {
      Swal.fire({
        title: "Medida incorrecta",
        text: `La imagen de la sucursal debe medir exactamente ${UBICACION_IMG_WIDTH} × ${UBICACION_IMG_HEIGHT} píxeles.`,
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }
    formData.append("imagen", archivoImagen);
  }

  try {
    const response = await fetch(`/manager/ubicaciones/put/${id}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
      },
      body: formData,
    });

    const data = await response.json();

    if (data.success) {
      Swal.fire({
        title: "¡Éxito!",
        text: data.message || "actualizado correctamente",
        icon: "success",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      }).then(() => window.location.reload(true));
    } else {
      Swal.fire({
        title: "Error",
        text: data.message || "Ocurrió un error al actualizar",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  } catch (error) {
    console.error(error);

    Swal.fire({
      title: "Error",
      text: "Error de conexión o inesperado",
      icon: "error",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });
  }
  });
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
        title: `¿Eliminar la ubicación "${nombre}"?`,
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
          const response = await fetch(`/manager/ubicaciones/delete/${id}/`, {
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
              text: data.message || "No se pudo eliminar la ubicación",
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
// FETCH UBICACIONES
//----------------

async function fetchUbicaciones(term, optionsContainer) {
    try {
        const res = await fetch(
            `/manager/ubicaciones/bodega/search/?search=${encodeURIComponent(term)}`
        );

        const data = await res.json();

        optionsContainer.innerHTML = "";

        const bodegas = data;

        if (!bodegas.length) {
            optionsContainer.innerHTML = `
                <div class="list-group-item text-muted">
                    Sin resultados
                </div>
            `;
            return;
        }

        optionsContainer.innerHTML += `
            <div class="list-group-item select-suggestions-title fw-bold">
                ${term ? "Resultados encontrados" : "Más utilizadas"}
            </div>
        `;

        bodegas.forEach((u) => {

            const texto = `${u.nombre}${u.codigo ? " | " + u.codigo : ""}`;

            optionsContainer.innerHTML += `
                <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${u.id}"
                        data-label="${texto}">
                    ${texto}
                </button>
            `;
        });

    } catch (error) {

        optionsContainer.innerHTML = `
            <div class="list-group-item text-danger">
                Error al cargar ubicaciones
            </div>
        `;

        console.error(error);
    }
}
initDropdown("bodegaid", fetchUbicaciones);
initDropdown("bodegaidedit", fetchUbicaciones);

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
    const item = e.target.closest(".list-group-item-action");
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
    const estabaAbierto = dropdown.classList.contains("show");

    document
      .querySelectorAll(".ubicaciones-bodega-select .dropdown-menu.show")
      .forEach((menu) => menu.classList.remove("show"));

    dropdown.classList.toggle("show", !estabaAbierto);

    if (dropdown.classList.contains("show") && remoteSearchFn) {
      optionsContainer.innerHTML = `
                <div class="list-group-item select-suggestions-title fw-bold">Más utilizadas</div>
                <div class="list-group-item text-muted">Cargando sugerencias...</div>
            `;
      await remoteSearchFn("", optionsContainer);
      searchInput.focus();
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

document.addEventListener("DOMContentLoaded", () => {
  const esBodega = document.getElementById("es_bodega");
  const esTienda = document.getElementById("es_tienda");
  const esBodegaEdit = document.getElementById("es_bodegaedit");
  const esTiendaEdit = document.getElementById("es_tiendaedit");

  const relacionSwitch = document.getElementById("relacion_bodega");
  const relacionSwitchEdit = document.getElementById("relacion_bodegaedit");

  const relacionContainer = document.getElementById("switch_relacion");
  const relacionContainerEdit = document.getElementById("switch_relacionedit");

  const bodegaContainer = document.getElementById("bodega_container");
  const bodegaContainerEdit = document.getElementById("bodega_containeredit");

  const tiendaExtraContainer = document.getElementById("tienda_extra_container");
  const tiendaExtraContainerEdit = document.getElementById("tienda_extra_containeredit");

  const bodegaInput = document.getElementById("bodegaid");
  const bodegaInputEdit = document.getElementById("bodegaidedit");

  // ------------------------
  // RESET BODEGA
  // ------------------------
  function resetBodega() {
    bodegaInput.value = "";

    const btn = bodegaContainer.querySelector("button");
    if (btn) btn.textContent = "Escriba para buscar...";
    bodegaContainer.querySelector(".dropdown-menu")?.classList.remove("show");
  }

  // RESET BODEGA (EDIT)
  // ------------------------
  function resetBodegaEdit() {
    bodegaInputEdit.value = "";

    const btn = bodegaContainerEdit.querySelector("button");
    if (btn) btn.textContent = "Escriba para buscar...";
    bodegaContainerEdit.querySelector(".dropdown-menu")?.classList.remove("show");
  }

  // ------------------------
  // ESTADO INICIAL
  // ------------------------
  relacionContainer.style.display = "none";
  bodegaContainer.hidden = true;
  if (tiendaExtraContainer) tiendaExtraContainer.hidden = true;
  relacionContainerEdit.style.display = "none";
  bodegaContainerEdit.hidden = true;
  if (tiendaExtraContainerEdit) tiendaExtraContainerEdit.hidden = true;

  // =========================
  // SI ES BODEGA
  // =========================
  esBodega.addEventListener("change", function () {
    if (this.checked) {
      esTienda.checked = false;

      relacionContainer.style.display = "none";
      relacionSwitch.checked = false;
      if (tiendaExtraContainer) tiendaExtraContainer.hidden = true;

      bodegaContainer.hidden = true;
      resetBodega();
    }
  });

  esBodegaEdit.addEventListener("change", function () {
    if (this.checked) {
      esTiendaEdit.checked = false;

      relacionContainerEdit.style.display = "none";
      relacionSwitchEdit.checked = false;
      if (tiendaExtraContainerEdit) tiendaExtraContainerEdit.hidden = true;

      bodegaContainerEdit.hidden = true;
      resetBodegaEdit();
    }
  });

  // =========================
  // SI ES TIENDA
  // =========================
  esTienda.addEventListener("change", function () {
    if (this.checked) {
      esBodega.checked = false;

      relacionContainer.style.display = "block";
      if (tiendaExtraContainer) tiendaExtraContainer.hidden = false;
    } else {
      relacionContainer.style.display = "none";
      relacionSwitch.checked = false;
      if (tiendaExtraContainer) tiendaExtraContainer.hidden = true;

      bodegaContainer.hidden = true;
      resetBodega();
    }
  });

  esTiendaEdit.addEventListener("change", function () {
    if (this.checked) {
      esBodegaEdit.checked = false;

      relacionContainerEdit.style.display = "block";
      if (tiendaExtraContainerEdit) tiendaExtraContainerEdit.hidden = false;
    } else {
      relacionContainerEdit.style.display = "none";
      relacionSwitchEdit.checked = false;
      if (tiendaExtraContainerEdit) tiendaExtraContainerEdit.hidden = true;

      bodegaContainerEdit.hidden = true;
      resetBodegaEdit();
    }
  });

  // =========================
  // SWITCH RELACIÓN BODEGA
  // =========================
  relacionSwitch.addEventListener("change", function () {
    if (this.checked) {
      bodegaContainer.hidden = false;
    } else {
      bodegaContainer.hidden = true;
      resetBodega();
    }
  });

  relacionSwitchEdit.addEventListener("change", function () {
    if (this.checked) {
      bodegaContainerEdit.hidden = false;
    } else {
      bodegaContainerEdit.hidden = true;
      resetBodegaEdit();
    }
  });
});
