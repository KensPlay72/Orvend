
console.log("client.js cargado");

//----------------
// REGISTRAR
//----------------
function valueOrNull(value) {
    if (value === undefined || value === null) return null;
    const v = value.trim();
    return v === "" ? null : v;
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('postregis');
    const btn = document.getElementById('btnregis');
    const modalElement = document.getElementById('modalregis');
    const modal = new bootstrap.Modal(modalElement);

    btn.addEventListener('click', async () => {
        if (form.dataset.submitting === "true") return;
        form.dataset.submitting = "true";

        const phoneNumber = document.getElementById("telefono").value;
        const fullPhone = valueOrNull(phoneNumber.trim());

        const payload = {
            dni: valueOrNull(document.getElementById('dni').value),
            nombre: valueOrNull(document.getElementById('pnombre').value),
            nombre2: valueOrNull(document.getElementById('snombre').value),
            apellido: valueOrNull(document.getElementById('papellido').value),
            apellido2: valueOrNull(document.getElementById('sapellido').value),
            empresa: valueOrNull(document.getElementById('nempresa').value),
            direccion: valueOrNull(document.getElementById('direccion').value),
            email: valueOrNull(document.getElementById('email').value),
            telefono: fullPhone
        };

        if (!payload.dni) {
            Swal.fire({
                title: "Error",
                text: "El DNI es obligatorio",
                icon: "warning",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            });
            form.dataset.submitting = "false";
            return;
        }

        try {
            const response = await fetch("/manager/clientes/post/", {
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
                    title: "Éxito",
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
        } finally {
            form.dataset.submitting = "false";
        }
    });
});

//----------------
// EDICION
//----------------
document.getElementById("btnput").addEventListener("click", async (e) => {
    e.preventDefault();

    const clienteId = document.getElementById("idedit").value;
    const dni = document.getElementById("dniedit").value.trim();

    if (!dni) {
        Swal.fire("Error", "El DNI es obligatorio", "error");
        return;
    }

    const phoneNumber = document.getElementById("telefonoedit").value;
    const fullPhone = valueOrNull(phoneNumber.trim());

    const payload = {
        dni: dni,
        nombre: valueOrNull(document.getElementById('pnombreedit').value),
        nombre2: valueOrNull(document.getElementById('snombreedit').value),
        apellido: valueOrNull(document.getElementById('papellidoedit').value),
        apellido2: valueOrNull(document.getElementById('sapellidoedit').value),
        empresa: valueOrNull(document.getElementById('nempresaedit').value),
        direccion: valueOrNull(document.getElementById('direccionedit').value),
        email: valueOrNull(document.getElementById('emailedit').value),
        telefono: fullPhone,
        isActive: document.getElementById("isActiveedit").checked
    };

    try {
        const response = await fetch(`/manager/clientes/put/${clienteId}/`, {
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
                text: data.message,
                icon: "success",
                confirmButtonText: "Aceptar",
                customClass: { confirmButton: "classbotones" }
            }).then(() => window.location.reload());
        } else {
            Swal.fire("Error", data.message, "error");
        }
    } catch (err) {
        console.error(err);
        Swal.fire("Error", "Error de conexión", "error");
    }
});


//----------------
// VALIDAR NUMERO EN INPUT
//----------------
function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, '');
}

// (El código de manejo de selects de código de país fue eliminado)


//----------------
// LLENAR FORMULARIO
//----------------
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', async (e) => {
    const button = e.target.closest('.btn-edit');
    if (!button) return;

    const clienteId = button.dataset.id;

    try {
      const response = await fetch(`/manager/clientes/get/${clienteId}/`);
      const data = await response.json();

      if (!data.success) {
        Swal.fire("Error", data.message || "No se pudo obtener la información", "error");
        return;
      }

      const cliente = data.cliente;

      document.getElementById('nempresaedit').value = cliente.empresa || '';
      document.getElementById('pnombreedit').value = cliente.nombre || '';
      document.getElementById('snombreedit').value = cliente.nombre2 || '';
      document.getElementById('papellidoedit').value = cliente.apellido || '';
      document.getElementById('sapellidoedit').value = cliente.apellido2 || '';
      document.getElementById('dniedit').value = cliente.dni || '';
      document.getElementById('emailedit').value = cliente.email || '';
      document.getElementById('direccionedit').value = cliente.direccion || '';
      document.getElementById('idedit').value = cliente.id || '';

      if (cliente.telefono) {
        document.getElementById('telefonoedit').value = cliente.telefono;
      }

      const activeCheckbox = document.getElementById("isActiveedit");
      const activeText = document.getElementById("activeTextedit");

      if (cliente.isActive) {
        activeCheckbox.checked = true;
        activeText.textContent = "Activo";
        activeText.classList.replace("text-danger", "text-success");
      } else {
        activeCheckbox.checked = false;
        activeText.textContent = "Inactivo";
        activeText.classList.replace("text-success", "text-danger");
      }

    } catch (err) {
      console.error(err);
      Swal.fire("Error", "Error de conexión", "error");
    }
  });
});

