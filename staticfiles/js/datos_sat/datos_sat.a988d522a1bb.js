//----------------
// REGISTRAR
//----------------
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("postregistro");
  const modalElement = document.getElementById("modalregis");
  const modal = new bootstrap.Modal(modalElement);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const rangoInicial = parseInt(
      document.getElementById("rango_inicial").value,
    );

    const rangoFinal = parseInt(document.getElementById("rango_final").value);

    // Validar rango
    if (rangoInicial >= rangoFinal) {
      Swal.fire({
        title: "Rango inválido",
        text: "El rango inicial debe ser menor que el rango final",
        icon: "warning",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });

      return;
    }

    const payload = {
      nombre_cai: document.getElementById("nombre_cai").value,
      numero_cai: document.getElementById("numero_cai").value,
      rango_inicial: document.getElementById("rango_inicial").value,
      rango_final: document.getElementById("rango_final").value,
      fecha_de_emision: document.getElementById("fecha_de_emision").value,
      fecha_de_vencimiento: document.getElementById("fecha_de_vencimiento")
        .value,
      id_sucursal: document.getElementById("id_sucursal").value,
    };

    try {
      const response = await fetch("/manager/datos_sat/post/", {
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
        Swal.fire({
          title: "¡Éxito!",
          text: data.message || "registrado correctamente",
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
      Swal.fire({
        title: "Error",
        text: "Error de conexión o inesperado. Ver consola para más detalles.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    }
  });
});
//--------------------
// LLENAR FORMULARIO
//--------------------
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".btn-edit").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.dataset.id;

      const response = await fetch(`/manager/datos_sat/get/${id}/`);

      const data = await response.json();

      if (data.success) {
        const sat = data.datos_sat;

        document.getElementById("id_satedit").value = sat.id;

        document.getElementById("nombre_caiedit").value = sat.nombre_cai;

        document.getElementById("numero_caiedit").value = sat.numero_cai;

        document.getElementById("rango_inicialedit").value = sat.rango_inicial;

        document.getElementById("rango_finaledit").value = sat.rango_final;

        document.getElementById("fecha_emisionedit").value =
          sat.fecha_de_emision;

        document.getElementById("fecha_vencimientoedit").value =
          sat.fecha_de_vencimiento;

        document.getElementById("sucursaledit").value = sat.id_sucursal;

        const check = document.getElementById("isActiveedit");
        const text = document.getElementById("activeTextedit");

        check.checked = sat.isActive;

        if (sat.isActive) {
          text.textContent = "Activo";
          text.className = "fw-bold text-success";
        } else {
          text.textContent = "Inactivo";
          text.className = "fw-bold text-danger";
        }
      }
    });
  });
});

//-----------------
//  EDICION
//-----------------
document.getElementById("putregistro").addEventListener("submit", async (e) => {
  e.preventDefault();

  const id = document.getElementById("id_satedit").value;

  const rangoInicial = parseInt(
    document.getElementById("rango_inicialedit").value,
  );

  const rangoFinal = parseInt(document.getElementById("rango_finaledit").value);

  // Validar rango
  if (rangoInicial >= rangoFinal) {
    Swal.fire({
      title: "Rango inválido",
      text: "El rango inicial debe ser menor que el rango final",
      icon: "warning",
      confirmButtonText: "Aceptar",
      customClass: { confirmButton: "classbotones" },
    });

    return;
  }

  const payload = {
    nombre_cai: document.getElementById("nombre_caiedit").value,

    numero_cai: document.getElementById("numero_caiedit").value,

    rango_inicial: rangoInicial,

    rango_final: rangoFinal,

    fecha_de_emision: document.getElementById("fecha_emisionedit").value,

    fecha_de_vencimiento: document.getElementById("fecha_vencimientoedit")
      .value,

    id_sucursal: document.getElementById("sucursaledit").value,
  };

  const isActiveCheckbox = document.getElementById("isActiveedit");
  if (!isActiveCheckbox.checked) payload.IsActive = false;

  const response = await fetch(`/manager/datos_sat/put/${id}/`, {
    method: "PUT",

    headers: {
      "Content-Type": "application/json",

      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },

    body: JSON.stringify(payload),
  });

  const data = await response.json();

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
      window.location.reload(true);
    });
  } else {
    Swal.fire("Error", data.message, "error");
  }
});
