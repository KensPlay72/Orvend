/*===== FOCUS =====*/
const inputs = document.querySelectorAll(".form__input");

/*=== Add focus ===*/
function addfocus() {
  let parent = this.parentNode.parentNode;
  parent.classList.add("focus");
}

/*=== Remove focus ===*/
function remfocus() {
  let parent = this.parentNode.parentNode;
  if (this.value == "") {
    parent.classList.remove("focus");
  }
}

/*=== To call function===*/
inputs.forEach((input) => {
  input.addEventListener("focus", addfocus);
  input.addEventListener("blur", remfocus);
});

//_____________________________________//
//

document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector(".form__content");

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    if (!username || !password) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "Llena todos los campos",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
      return;
    }

    document.getElementById("loader").style.display = "flex";

    try {
      const response = await fetch("/accounts/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        Swal.fire({
          icon: "error",
          title: "Error",
          text: data.message || "Error desconocido",
          confirmButtonText: "Aceptar",
          customClass: { confirmButton: "classbotones" },
        });
        return;
      }

      // ✔ ÉXITO → redirect directo
      window.location.href = "/manager/dashboard/";
    } catch (error) {
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "Error de conexión con el servidor",
        confirmButtonText: "Aceptar",
        customClass: { confirmButton: "classbotones" },
      });
    } finally {
      document.getElementById("loader").style.display = "none";
    }
  });
});

function getCookie(name) {
  let cookieValue = null;

  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");

    for (let cookie of cookies) {
      cookie = cookie.trim();

      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }

  return cookieValue;
}
