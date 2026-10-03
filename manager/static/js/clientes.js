//----------------
// REGISTRAR
//----------------
function valueOrNull(value) {
  if (value === undefined || value === null) return null;
  const v = value.trim();
  return v === "" ? null : v;
}

document.addEventListener("DOMContentLoaded", () => {
  const boton = document.getElementById("exportarClientesExcel");
  if (!boton) return;

  const icono = boton.querySelector("i");
  const iconoOriginal = "bx bx-spreadsheet";

  boton.addEventListener("click", async () => {
    const busqueda = document.getElementById("busqueda")?.value || "";
    boton.disabled = true;
    icono.className = "bx bx-loader-alt bx-spin";

    try {
      const parametros = new URLSearchParams({ search: busqueda });
      const respuesta = await fetch(`${boton.dataset.exportUrl}?${parametros}`);
      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const archivo = await respuesta.blob();
      const enlace = document.createElement("a");
      enlace.href = URL.createObjectURL(archivo);
      enlace.download = "clientes.xlsx";
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(enlace.href);
    } catch (error) {
      Swal.fire("Error", "No se pudo exportar el listado de clientes", "error");
    } finally {
      boton.disabled = false;
      icono.className = iconoOriginal;
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("postregis");
  const btn = document.getElementById("btnregis");
  const modalElement = document.getElementById("modalregis");

  const modal = new bootstrap.Modal(modalElement);

  // ==========================================================
  // REGISTRAR CLIENTE
  // ==========================================================

  btn.addEventListener("click", async () => {
    if (form.dataset.submitting === "true") {
      return;
    }

    form.dataset.submitting = "true";

    // ==========================================================
    // DATOS
    // ==========================================================

    const phoneNumber = document.getElementById("telefono").value;

    const fullPhone = valueOrNull(phoneNumber.trim());

    const payload = {
      dni: valueOrNull(document.getElementById("dni").value),

      nombre: valueOrNull(document.getElementById("pnombre").value),

      nombre2: valueOrNull(document.getElementById("snombre").value),

      apellido: valueOrNull(document.getElementById("papellido").value),

      apellido2: valueOrNull(document.getElementById("sapellido").value),

      empresa: valueOrNull(document.getElementById("nempresa").value),

      direccion: valueOrNull(document.getElementById("direccion").value),

      email: valueOrNull(document.getElementById("email").value),

      telefono: fullPhone,

      enviar_factura_whatsapp: Boolean(
        document.getElementById("enviarFacturaWhatsapp")?.checked,
      ),

      pais: valueOrNull(document.getElementById("pais").value),

      departamento: valueOrNull(document.getElementById("departamento").value),

      municipio: valueOrNull(document.getElementById("municipio").value),

      d_credito: valueOrNull(document.getElementById("d_credito")?.value),

      max_credito: valueOrNull(document.getElementById("max_credito")?.value),
    };

    // ==========================================================
    // VALIDACION
    // ==========================================================

    if (!payload.dni) {
      Swal.fire({
        title: "Error",
        text: "El DNI es obligatorio",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });

      form.dataset.submitting = "false";

      return;
    }

    // ==========================================================
    // ENVIO
    // ==========================================================

    try {
      const response = await fetch("/manager/clientes/post/", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
            .value,
        },

        body: JSON.stringify(payload),
      });

      const data = await response.json();

      // ======================================================
      // RESPUESTA EXITOSA
      // ======================================================

      if (data.success) {
        modal.hide();

        form.reset();

        Swal.fire({
          title: "Éxito",
          text: data.message,
          icon: "success",
          confirmButtonText: "Aceptar",
          customClass: {
            confirmButton: "classbotones",
          },
        }).then(() => {
          window.location.reload();
        });
      } else {
        // ==================================================
        // ERROR DEL SERVIDOR
        // ==================================================

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
        text: "No se pudo registrar el cliente",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: {
          confirmButton: "classbotones",
        },
      });
    } finally {
      form.dataset.submitting = "false";
    }
  });
});
//----------------
// VALIDAR NUMERO EN INPUT
//----------------
function validateNumber(input) {
  input.value = input.value.replace(/[^0-9.+]/g, "");
}

// ==========================================================
// LLENAR FORMULARIO DE EDICION
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {
  document.addEventListener("click", async (e) => {
    const button = e.target.closest(".btn-edit");

    if (!button) {
      return;
    }

    const clienteId = button.dataset.id;

    try {
      const response = await fetch(`/manager/clientes/get/${clienteId}/`);

      const data = await response.json();

      if (!data.success) {
        Swal.fire(
          "Error",
          data.message || "No se pudo obtener la información",
          "error",
        );

        return;
      }

      const cliente = data.cliente;

      // ======================================================
      // ID
      // ======================================================

      document.getElementById("idedit").value = cliente.id || "";

      // ======================================================
      // DATOS PERSONALES
      // ======================================================

      document.getElementById("pnombreedit").value = cliente.nombre || "";

      document.getElementById("snombreedit").value = cliente.nombre2 || "";

      document.getElementById("papellidoedit").value = cliente.apellido || "";

      document.getElementById("sapellidoedit").value = cliente.apellido2 || "";

      // ======================================================
      // EMPRESA
      // ======================================================

      document.getElementById("nempresaedit").value = cliente.empresa || "";

      // ======================================================
      // IDENTIFICACION
      // ======================================================

      document.getElementById("dniedit").value = cliente.dni || "";

      // ======================================================
      // CONTACTO
      // ======================================================

      document.getElementById("emailedit").value = cliente.email || "";

      document.getElementById("telefonoedit").value = cliente.telefono || "";

      const enviarFacturaWhatsappEdit = document.getElementById(
        "enviarFacturaWhatsappedit",
      );

      if (enviarFacturaWhatsappEdit) {
        enviarFacturaWhatsappEdit.checked = Boolean(
          cliente.enviar_factura_whatsapp,
        );
      }

      // ======================================================
      // DIRECCION
      // ======================================================

      document.getElementById("direccionedit").value = cliente.direccion || "";

      // ======================================================
      // UBICACION
      // ======================================================

      document.getElementById("paisedit").value = cliente.pais || "";

      document.getElementById("departamentoedit").value =
        cliente.departamento || "";

      document.getElementById("municipioedit").value = cliente.municipio || "";

      // ======================================================
      // CREDITO
      // ======================================================

      const dCreditoEdit = document.getElementById("d_creditoedit");
      const maxCreditoEdit = document.getElementById("max_creditoedit");

      if (dCreditoEdit) {
        dCreditoEdit.value = cliente.d_credito ?? "";
      }

      if (maxCreditoEdit) {
        maxCreditoEdit.value = cliente.max_credito ?? "";
      }

      // ======================================================
      // ESTADO
      // ======================================================

      const activeCheckbox = document.getElementById("isActiveedit");

      const activeText = document.getElementById("activeTextedit");

      if (cliente.isActive) {
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
    } catch (err) {
      console.error(err);

      Swal.fire("Error", "Error de conexión", "error");
    }
  });
});

// ==========================================================
// ACTUALIZAR CLIENTE
// ==========================================================

document.getElementById("btnput").addEventListener("click", async (e) => {
  e.preventDefault();

  // ======================================================
  // ID
  // ======================================================

  const clienteId = document.getElementById("idedit").value;

  // ======================================================
  // DNI
  // ======================================================

  const dni = document.getElementById("dniedit").value.trim();

  if (!dni) {
    Swal.fire("Error", "El DNI es obligatorio", "error");

    return;
  }

  // ======================================================
  // TELEFONO
  // ======================================================

  const phoneNumber = document.getElementById("telefonoedit").value;

  const fullPhone = valueOrNull(phoneNumber.trim());

  // ======================================================
  // DATOS
  // ======================================================

  const payload = {
    dni: dni,

    nombre: valueOrNull(document.getElementById("pnombreedit").value),

    nombre2: valueOrNull(document.getElementById("snombreedit").value),

    apellido: valueOrNull(document.getElementById("papellidoedit").value),

    apellido2: valueOrNull(document.getElementById("sapellidoedit").value),

    empresa: valueOrNull(document.getElementById("nempresaedit").value),

    direccion: valueOrNull(document.getElementById("direccionedit").value),

    email: valueOrNull(document.getElementById("emailedit").value),

    telefono: fullPhone,

    enviar_factura_whatsapp: Boolean(
      document.getElementById("enviarFacturaWhatsappedit")?.checked,
    ),

    pais: valueOrNull(document.getElementById("paisedit").value),

    departamento: valueOrNull(
      document.getElementById("departamentoedit").value,
    ),

    municipio: valueOrNull(document.getElementById("municipioedit").value),

    d_credito: valueOrNull(document.getElementById("d_creditoedit")?.value),

    max_credito: valueOrNull(document.getElementById("max_creditoedit")?.value),

    isActive: document.getElementById("isActiveedit").checked,
  };

  // ======================================================
  // ENVIAR
  // ======================================================

  try {
    const response = await fetch(`/manager/clientes/put/${clienteId}/`, {
      method: "PUT",

      headers: {
        "Content-Type": "application/json",

        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")
          .value,
      },

      body: JSON.stringify(payload),
    });

    const data = await response.json();

    // ==================================================
    // RESPUESTA
    // ==================================================

    if (data.success) {
      Swal.fire({
        title: "¡Éxito!",

        text: data.message,

        icon: "success",

        confirmButtonText: "Aceptar",

        customClass: {
          confirmButton: "classbotones",
        },
      }).then(() => {
        window.location.reload();
      });
    } else {
      Swal.fire("Error", data.message, "error");
    }
  } catch (err) {
    console.error(err);

    Swal.fire("Error", "Error de conexión", "error");
  }
});
