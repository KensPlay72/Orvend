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
//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("postregistro");
  const modalElement = document.getElementById("modalregis");
  const modal = new bootstrap.Modal(modalElement);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      // =========================
      // PRINCIPAL
      // =========================
      nombre: document.getElementById("nubicacion").value.trim(),

      es_bodega: document.getElementById("es_bodega").checked,
      es_tienda: document.getElementById("es_tienda").checked,

      codigo: document.getElementById("cubicacion").value.trim(),

      // =========================
      // RELACIÓN BODEGA (SOLO TIENDA)
      // =========================
      relacion_bodega:
        document.getElementById("relacion_bodega")?.checked || false,

      bodega_id: document.getElementById("bodegaid").value || null,
    };

    try {
      const response = await fetch("/manager/ubicaciones/post/", {
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

        // reset UI visual
        document.getElementById("bodega_container").style.display = "none";
        document.getElementById("switch_relacion").style.display = "none";

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

        document.getElementById("cubicacionedit").value =
          ubicacion.codigo || "";

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

        // =========================
        // MOSTRAR RELACION SI ES TIENDA
        // =========================

        if (ubicacion.es_tienda) {
          switchRelacion.style.display = "block";

          // =========================
          // TIENE BODEGA RELACIONADA
          // =========================

          if (ubicacion.bodegaid) {
            relacionBodega.checked = true;

            bodegaContainer.style.display = "block";

            document.getElementById("bodegaidedit").value = ubicacion.bodegaid;

            const btnBodega = document.querySelector(
              "#bodega_containeredit button",
            );

            btnBodega.textContent =
              ubicacion.bodeganombre || "Seleccionar bodega";
          } else {
            relacionBodega.checked = false;

            bodegaContainer.style.display = "none";

            document.getElementById("bodegaidedit").value = "";

            const btnBodega = document.querySelector(
              "#bodega_containeredit button",
            );

            btnBodega.textContent = "Escriba para buscar...";
          }
        } else {
          switchRelacion.style.display = "none";

          relacionBodega.checked = false;

          bodegaContainer.style.display = "none";

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
document.getElementById("putregistro").addEventListener("submit", async (e) => {
  e.preventDefault();

  const id = document.getElementById("idedit").value;

  const payload = {
    Nombre: document.getElementById("nubicacionedit").value,
    Codigo: document.getElementById("cubicacionedit").value,

    // TIPOS
    es_bodega: document.getElementById("es_bodegaedit").checked,
    es_tienda: document.getElementById("es_tiendaedit").checked,

    // RELACIÓN
    relacion_bodega: document.getElementById("relacion_bodegaedit")
      ? document.getElementById("relacion_bodegaedit").checked
      : false,

    bodegaid: document.getElementById("bodegaidedit").value || null,
  };

  // si no quiere relación o no es tienda → null
  if (!payload.es_tienda || !payload.relacion_bodega) {
    payload.bodegaid = null;
  }

  // ACTIVE
  payload.IsActive = document.getElementById("isActiveedit").checked;

  try {
    const response = await fetch(`/manager/ubicaciones/put/${id}/`, {
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
// FETCH UBICACIONES
//----------------
async function fetchUbicaciones(term, optionsContainer) {
  try {
    const res = await fetch(
      `/manager/ubicaciones/search/?search=${encodeURIComponent(term)}`,
    );

    const data = await res.json();

    optionsContainer.innerHTML = "";

    if (!data.length) {
      optionsContainer.innerHTML = `
        <div class="list-group-item text-muted">Sin resultados</div>
      `;
      return;
    }

    optionsContainer.innerHTML += `
      <div class="list-group-item active bg-light text-dark fw-bold">
        ${term ? "Resultados encontrados" : "Sugerencias recientes"}
      </div>
    `;

    data.forEach((u) => {
      // =========================
      // TIPO LABEL
      // =========================
      let tipoLabel = "";

      if (u.es_bodega) {
        tipoLabel = "Bodega";
      } else if (u.es_tienda) {
        tipoLabel = "Tienda";
      } else {
        tipoLabel = "Sin tipo";
      }

      // =========================
      // TEXTO FINAL
      // =========================
      const texto = `${u.nombre}${u.codigo ? " | " + u.codigo : ""} | ${tipoLabel}`;

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

  const bodegaInput = document.getElementById("bodegaid");
  const bodegaInputEdit = document.getElementById("bodegaidedit");

  // ------------------------
  // RESET BODEGA
  // ------------------------
  function resetBodega() {
    bodegaInput.value = "";

    const btn = bodegaContainer.querySelector("button");
    if (btn) btn.textContent = "Escriba para buscar...";
  }

  // RESET BODEGA (EDIT)
  // ------------------------
  function resetBodegaEdit() {
    bodegaInputEdit.value = "";

    const btn = bodegaContainerEdit.querySelector("button");
    if (btn) btn.textContent = "Escriba para buscar...";
  }

  // ------------------------
  // ESTADO INICIAL
  // ------------------------
  relacionContainer.style.display = "none";
  bodegaContainer.style.display = "none";
  relacionContainerEdit.style.display = "none";
  bodegaContainerEdit.style.display = "none";

  // =========================
  // SI ES BODEGA
  // =========================
  esBodega.addEventListener("change", function () {
    if (this.checked) {
      esTienda.checked = false;

      relacionContainer.style.display = "none";
      relacionSwitch.checked = false;

      bodegaContainer.style.display = "none";
      resetBodega();
    }
  });

  esBodegaEdit.addEventListener("change", function () {
    if (this.checked) {
      esTiendaEdit.checked = false;

      relacionContainerEdit.style.display = "none";
      relacionSwitchEdit.checked = false;

      bodegaContainerEdit.style.display = "none";
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
    } else {
      relacionContainer.style.display = "none";
      relacionSwitch.checked = false;

      bodegaContainer.style.display = "none";
      resetBodega();
    }
  });

  esTiendaEdit.addEventListener("change", function () {
    if (this.checked) {
      esBodegaEdit.checked = false;

      relacionContainerEdit.style.display = "block";
    } else {
      relacionContainerEdit.style.display = "none";
      relacionSwitchEdit.checked = false;

      bodegaContainerEdit.style.display = "none";
      resetBodegaEdit();
    }
  });

  // =========================
  // SWITCH RELACIÓN BODEGA
  // =========================
  relacionSwitch.addEventListener("change", function () {
    if (this.checked) {
      bodegaContainer.style.display = "block";
    } else {
      bodegaContainer.style.display = "none";
      resetBodega();
    }
  });

  relacionSwitchEdit.addEventListener("change", function () {
    if (this.checked) {
      bodegaContainerEdit.style.display = "block";
    } else {
      bodegaContainerEdit.style.display = "none";
      resetBodegaEdit();
    }
  });
});
