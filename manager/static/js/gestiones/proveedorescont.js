//----------------
// REGISTRAR 
//----------------
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById("postregistro");
    const modalElement = document.getElementById("modalregis");
    const modal = new bootstrap.Modal(modalElement);
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

  const countryCode = document.getElementById("countryCode").value;
  const phoneNumber = document.getElementById("telefono").value;
  const fullPhone = countryCode ? `${countryCode} ${phoneNumber}` : phoneNumber;


  const payload = {
    proveedor: document.getElementById("proveedoresid").value,
    nombre: document.getElementById("ncontacto").value,
    Puesto: document.getElementById("puesto").value,
    Telefono: fullPhone,
    Email: document.getElementById("email").value,
    Observaciones: document.getElementById("observacion").value,
  };

  try {
    const response = await fetch("/manager/proveedores/contactos/post/", {
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
  }
  });
});     


//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {

            const proveedorId = button.getAttribute("data-id");
            const response = await fetch(`/manager/proveedores/contactos/get/${proveedorId}/`);
            const data = await response.json();

            if (!data.success) {
                Swal.fire("Error", data.message || "No se pudo obtener la información", "error");
                return;
            }

            const proveedorcont = data.proveedorcont;

            // ------------------------
            // Campos básicos
            // ------------------------
            document.getElementById("idedit").value = proveedorcont.id;
            document.getElementById("ncontactoedit").value = proveedorcont.nombre;
            document.getElementById("puestoedit").value = proveedorcont.puesto;
            document.getElementById("emailedit").value = proveedorcont.email;
            document.getElementById("observacionedit").value = proveedorcont.observaciones;

            // ------------------------
            // Teléfono
            // ------------------------
            if (proveedorcont.telefono) {
                const partes = proveedorcont.telefono.split(" ");
                document.getElementById("countryCodeedit").value = partes[0] || "";
                document.getElementById("telefonoedit").value = partes[1] || "";
            }

            // ------------------------
            // SELECT PERSONALIZADO PROVEEDOR
            // ------------------------
            const hiddenInput = document.getElementById("proveedoresidedit");
            const selectContainer = hiddenInput.nextElementSibling;
            const dropdownBtn = selectContainer.querySelector("button");
            const optionsContainer = selectContainer.querySelector(".options");
            const searchInput = selectContainer.querySelector(".search-box input");

            if (proveedorcont.proveedores && proveedorcont.proveedores.id) {

                // ID real
                hiddenInput.value = proveedorcont.proveedores.id;

                // Texto visible
                dropdownBtn.textContent =`${proveedorcont.proveedores.nombre_legal} | ${proveedorcont.proveedores.nombre_comercial}`;

                // IMPORTANTE: pintar opción dentro del dropdown
                optionsContainer.innerHTML = `
                    <button type="button"
                        class="list-group-item list-group-item-action"
                        data-value="${proveedorcont.proveedores.id}">
                        ${proveedorcont.proveedores.nombre_comercial}
                    </button>
                `;

            } else {
                hiddenInput.value = "";
                dropdownBtn.textContent = "Proveedor no asignado";

                optionsContainer.innerHTML = `
                    <div class="list-group-item text-muted">
                        Sin proveedor asignado
                    </div>
                `;
            }

            // limpiar búsqueda previa
            if (searchInput) searchInput.value = "";

            // ------------------------
            // Estado
            // ------------------------
            const activeCheckbox = document.getElementById("isActiveedit");
            const activeText = document.getElementById("activeTextedit");

            if (proveedorcont.is_active) {
                activeCheckbox.checked = true;
                activeText.textContent = "Activo";
                activeText.classList.remove("text-danger");
                activeText.classList.add("text-success");
            } else {
                activeCheckbox.checked = false;
                activeText.textContent = "Inactivo";
                activeText.classList.remove("text-success");
                activeText.classList.add("text-danger");
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
      nombre: document.getElementById("ncontactoedit").value,
      puesto: document.getElementById("puestoedit").value,
      email: document.getElementById("emailedit").value,
      observaciones: document.getElementById("observacionedit").value,
      telefono: document.getElementById("countryCodeedit").value + " " + document.getElementById("telefonoedit").value,
      is_active: document.getElementById("isActiveedit").checked,
      proveedor: document.getElementById("proveedoresidedit").value,
    }
      try {
        const response = await fetch(`/manager/proveedores/contactos/put/${id}/`, {
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
                    const response = await fetch(`/manager/proveedores/contactos/delete/${userId}/`, {
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

// Inicializar
initDropdown("proveedoresid", fetchProveedores);
initDropdown("proveedoresidedit", fetchProveedores);



//----------------
// CODIGO EN TELEFONO
//----------------
document.addEventListener('DOMContentLoaded', () => {
  loadCountryCodes();

  const select = document.getElementById('countryCode');
  const select2 = document.getElementById('countryCodeedit');

  function setupSelectBehavior(sel) {
    // Mostrar solo el código al seleccionar
    sel.addEventListener('change', () => {
      const selected = sel.selectedOptions[0];
      if (selected) selected.textContent = selected.value;
    });

    // Mostrar nombre + código cuando abro
    sel.addEventListener('mousedown', () => {
      Array.from(sel.options).forEach(opt => {
        if (opt.dataset.label) {
          opt.textContent = opt.dataset.label;
        }
      });
    });

    // Al cerrar (perder foco), restaurar solo el código
    sel.addEventListener('blur', () => {
      const selected = sel.selectedOptions[0];
      if (selected) selected.textContent = selected.value;
    });
  }

  setupSelectBehavior(select);
  setupSelectBehavior(select2);
});

async function loadCountryCodes() {
  try {
    const res = await fetch('https://restcountries.com/v3.1/all?fields=name,idd');
    const data = await res.json();

    const countries = Array.isArray(data) ? data : [];
    const select = document.getElementById('countryCode');
    const select2 = document.getElementById('countryCodeedit');

    countries.sort((a, b) => (a.name?.common || '').localeCompare(b.name?.common || ''));

    countries.forEach(country => {
      if (country.idd?.root) {
        const code = country.idd.root + (country.idd.suffixes ? country.idd.suffixes[0] : '');

        const option = document.createElement('option');
        option.value = code;
        option.dataset.label = `${country.name.common} (${code})`;
        option.textContent = code; 

        const option2 = option.cloneNode(true);
        option2.dataset.label = option.dataset.label;

        select.appendChild(option);
        select2.appendChild(option2);
      }
    });
  } catch (error) {
    console.error("Error cargando códigos de país:", error);
  }
}