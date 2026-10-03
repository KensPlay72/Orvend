document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-view").forEach((btn) => {
    btn.addEventListener("click", function () {
      const devolucionToken = this.dataset.token;
      window.location.href = `/manager/compras/devoluciones/detalles/${devolucionToken}/`;
    });
  });
});

document.addEventListener("DOMContentLoaded", function () {
  const token = window.location.pathname.split("/").filter(Boolean).pop();

  // ====================================
  // APROBAR DEVOLUCIÓN
  // ====================================
  const btnAprobar = document.getElementById("btnAprobar");
  const modalResolucionEl = document.getElementById(
    "modalResolucionDevolucion",
  );
  const selectResolucion = document.getElementById("resolucionDevolucion");
  const btnConfirmarResolucion = document.getElementById(
    "confirmarResolucionDevolucion",
  );

  if (btnAprobar) {
    btnAprobar.addEventListener("click", function () {
      selectResolucion.value = "";
      bootstrap.Modal.getOrCreateInstance(modalResolucionEl).show();
    });
  }

  btnConfirmarResolucion?.addEventListener("click", async function () {
    const resolucion = selectResolucion.value;
    if (!resolucion) {
      Swal.fire({
        icon: "warning",
        title: "Selecciona una resolución",
        text: "Indica si el proveedor hará un cambio o dejará saldo a favor.",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

    try {
      btnConfirmarResolucion.disabled = true;
      const res = await fetch(`/manager/compras/devoluciones/aprobar/${token}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ resolucion }),
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.message || "No se pudo aprobar la devolución.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Devolucion_Aprobada.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      bootstrap.Modal.getInstance(modalResolucionEl)?.hide();

      const mensaje =
        resolucion === "CAMBIO"
          ? "Se generó una compra de reposición y la nota de devolución."
          : "El importe fue acreditado al saldo a favor del proveedor.";
      Swal.fire({
        title: "Devolución aprobada",
        text: mensaje,
        icon: "success",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      }).then(() => {
        window.location.href = "/manager/compras/devoluciones/";
      });
    } catch (error) {
      console.error(error);
      Swal.fire({
        title: "Error",
        text: error.message || "No se pudo aprobar la devolución.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      btnConfirmarResolucion.disabled = false;
    }
  });

  // ====================================
  // RECHAZAR DEVOLUCIÓN
  // ====================================
  const btnRechazar = document.getElementById("btnRechazar");
  const modalRechazoEl = document.getElementById("modalRechazoDevolucion");
  const motivoRechazo = document.getElementById("motivoRechazoDevolucion");
  const btnConfirmarRechazo = document.getElementById(
    "confirmarRechazoDevolucion",
  );

  if (btnRechazar) {
    btnRechazar.addEventListener("click", function () {
      motivoRechazo.value = "";
      motivoRechazo.classList.remove("is-invalid");
      bootstrap.Modal.getOrCreateInstance(modalRechazoEl).show();
    });
  }

  btnConfirmarRechazo?.addEventListener("click", async function () {
    const motivo = motivoRechazo.value.trim();
    if (!motivo) {
      motivoRechazo.focus();
      motivoRechazo.classList.add("is-invalid");
      return;
    }
    motivoRechazo.classList.remove("is-invalid");

    const result = await Swal.fire({
      title: "¿Rechazar devolución?",
      text: "Esta acción finalizará la devolución como rechazada.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, rechazar",
      cancelButtonText: "Cancelar",
      customClass: { confirmButton: "classbotones", cancelButton: "btn btn-secondary" },
    });
    if (!result.isConfirmed) return;

    try {
      btnConfirmarRechazo.disabled = true;
      const res = await fetch(`/manager/compras/devoluciones/rechazar/${token}/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ motivo }),
      });
      if (!res.ok) throw new Error("Error al rechazar");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Devolucion_Rechazada.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      bootstrap.Modal.getInstance(modalRechazoEl)?.hide();

      Swal.fire({
        title: "Devolución rechazada",
        text: "El documento fue generado correctamente.",
        icon: "success",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      }).then(() => {
        window.location.href = "/manager/compras/devoluciones/";
      });
    } catch (error) {
      console.error(error);
      Swal.fire({
        title: "Error",
        text: "No se pudo rechazar la devolución.",
        icon: "error",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      btnConfirmarRechazo.disabled = false;
    }
  });
});

// ====================================
// CSRF TOKEN
// ====================================
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");

    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();

      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
