/*==================== SHOW NAVBAR ====================*/
const showMenu = (headerToggle, navbarId) =>{
    const toggleBtn = document.getElementById(headerToggle),
    nav = document.getElementById(navbarId)
    
    // Validate that variables exist
    if(headerToggle && navbarId){
        toggleBtn.addEventListener('click', ()=>{
            // We add the show-menu class to the div tag with the nav__menu class
            nav.classList.toggle('show-menu')
            // change icon
            toggleBtn.classList.toggle('bx-x')
        })
    }
}
showMenu('header-toggle','navbar')

/*==================== LINK ACTIVE ====================*/
const linkColor = document.querySelectorAll('.nav__link')

function colorLink(){
    linkColor.forEach(l => l.classList.remove('active'))
    this.classList.add('active')
}

linkColor.forEach(l => l.addEventListener('click', colorLink))

//---------------------------------

// Obtener los elementos
  const profileImg = document.getElementById('profile-img');
  const modal      = document.getElementById('modal');

  /* ──────────────────────────────────────────────────────────
     Helpers
  ────────────────────────────────────────────────────────── */
  const showModal = () => {
    modal.style.display = 'block';          // primero mostrar
    requestAnimationFrame(() => {           // luego animar con suavidad
      modal.style.opacity   = '1';
      modal.style.transform = 'translateX(-50%) translateY(0)';
    });
  };

  const hideModal = () => {
    modal.style.opacity   = '0';
    modal.style.transform = 'translateX(-50%) translateY(20px)';
    // Espera a que termine la transición para ocultar totalmente
    modal.addEventListener('transitionend', () => {
      modal.style.display = 'none';
    }, { once: true });
  };

  /* ──────────────────────────────────────────────────────────
     Toggle al clicar el círculo de iniciales
  ────────────────────────────────────────────────────────── */
  profileImg.addEventListener('click', (e) => {
    e.stopPropagation();                    // evita que se propague al doc
    modal.style.display === 'block' ? hideModal() : showModal();
  });

  /* ──────────────────────────────────────────────────────────
     Cerrar si se hace clic fuera del modal
  ────────────────────────────────────────────────────────── */
  document.addEventListener('click', (e) => {
    // Si el modal está abierto y el clic NO fue dentro de él
    if (modal.style.display === 'block' && !modal.contains(e.target)) {
      hideModal();
    }
  });

  /* ──────────────────────────────────────────────────────────
     Cerrar sesion
  ────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", function () {

    const btn = document.getElementById("btn-logout");

    if (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();

            Swal.fire({
                title: "¿Cerrar sesión?",
                text: "Tu sesión se cerrará y tendrás que iniciar sesión nuevamente.",
                icon: "warning",
                showCancelButton: true,
                confirmButtonText: "Sí, cerrar sesión",
                cancelButtonText: "Cancelar",
                confirmButtonColor: "#d33",   // rojo
                cancelButtonColor: "#6c757d"  // gris
            }).then((result) => {

                if (result.isConfirmed) {

                    fetch("/accounts/api/logout/", {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": getCookie("csrftoken")
                        }
                    })
                    .then(() => {
                        window.location.href = "/accounts/login/";
                    })
                    .catch(error => {
                        console.error("Error logout:", error);
                        window.location.href = "/accounts/login/";
                    });
                }

            });
        });
    }
});


// CSRF helper
function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let cookie of cookies) {
            cookie = cookie.trim();

            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}