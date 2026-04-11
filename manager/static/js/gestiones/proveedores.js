//----------------
// REGISTRAR 
//----------------
document.getElementById("postregistro").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = document.getElementById("postregistro");
    const modalElement = document.getElementById("modalregis");
    const modal = new bootstrap.Modal(modalElement);

    const requiredFields = [
        { id: 'nlegal', name: 'Nombre Legal' },
        { id: 'ncomercial', name: 'Nombre Comercial' },
        { id: 'rtn', name: 'RTN' },
        { id: 'dcreditos', name: 'Días de Crédito' },
        { id: 'countryCode', name: 'Código de País' },
        { id: 'telefono', name: 'Teléfono' },
        { id: 'email', name: 'Email' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);
            input.classList.add('input-error');
            if (label) label.classList.add('text-error');
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
    const fullPhone = `${document.getElementById("countryCode").value} ${document.getElementById("telefono").value}`;

    const payload = {
        nombre_legal: document.getElementById("nlegal").value.trim(),
        nombre_comercial: document.getElementById("ncomercial").value.trim(),
        rtn: document.getElementById("rtn").value.trim(),
        dias_credito: document.getElementById("dcreditos").value.trim(),
        telefono: fullPhone.trim(),
        email: document.getElementById("email").value.trim()
    };

    try {
        const response = await fetch("/manager/proveedores/post/", {
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
            }).then(() => window.location.reload());
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

//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".btn-edit").forEach(button => {
        button.addEventListener("click", async () => {
            const proveedorId = button.getAttribute("data-id");
            const response = await fetch(`/manager/proveedores/get/${proveedorId}/`);
            const data = await response.json();
            
            if (data.success) {
                const proveedor = data.proveedor;

                // Llenar campos básicos
                document.getElementById("idproveedor").value = proveedor.id;
                document.getElementById("nlegaledit").value = proveedor.nombre_legal;
                document.getElementById("ncomercialedit").value = proveedor.nombre_comercial;
                document.getElementById("rtnedit").value = proveedor.rtn;
                document.getElementById("dcreditosedit").value = proveedor.dias_credito;
                document.getElementById("emailedit").value = proveedor.email;

                // Dividir teléfono en código y número
                if (proveedor.telefono) {
                    const partes = proveedor.telefono.split(" ");
                    const codigo = partes[0] || "";
                    const numero = partes[1] || "";

                    document.getElementById("countryCodeedit").value = codigo;
                    document.getElementById("telefonoedit").value = numero;
                }

                // Estado
                const activeCheckbox = document.getElementById("isActiveedit");
                const activeText = document.getElementById("activeTextedit");

                if (proveedor.is_active) {
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
            } else {
                Swal.fire("Error", data.message || "No se pudo obtener la información", "error");
            }
        });
    });
});


//----------------
// EDICION
//----------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
    e.preventDefault();

    const requiredFields = [
        { id: 'nlegaledit', name: 'Nombre Legal' },
        { id: 'ncomercialedit', name: 'Nombre Comercial' },
        { id: 'rtnedit', name: 'RTN' },
        { id: 'dcreditosedit', name: 'Días de Crédito' },
        { id: 'countryCodeedit', name: 'Código de País' },
        { id: 'telefonoedit', name: 'Teléfono' },
        { id: 'emailedit', name: 'Email' }
    ];

    let missingFields = [];

    requiredFields.forEach(field => {
        const input = document.getElementById(field.id);
        const formGroup = input.closest('.form-group');
        const label = formGroup ? formGroup.querySelector('label') : null;

        input.classList.remove('input-error');
        if (label) label.classList.remove('text-error');

        if (!input.value || input.value.trim() === '') {
            missingFields.push(field.name);
            input.classList.add('input-error');
            if (label) label.classList.add('text-error');
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

    const idproveedor = document.getElementById("idproveedor").value;
    const payload = {
        nombre_legal: document.getElementById("nlegaledit").value.trim(),
        nombre_comercial: document.getElementById("ncomercialedit").value.trim(),
        rtn: document.getElementById("rtnedit").value.trim(),
        dias_credito: document.getElementById("dcreditosedit").value.trim(),
        telefono: document.getElementById("countryCodeedit").value.trim() + " " + document.getElementById("telefonoedit").value.trim(),
        email: document.getElementById("emailedit").value.trim(),
        IsActive: document.getElementById("isActiveedit").checked
    };

    try {
        const response = await fetch(`/manager/proveedores/put/${idproveedor}/`, {
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
                    const response = await fetch(`/manager/proveedores/delete/${userId}/`, {
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