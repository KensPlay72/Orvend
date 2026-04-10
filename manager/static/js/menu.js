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
  document.getElementById("btn-logout").onclick = function() {
    fetch("/logout/", {
        method: "GET",
        credentials: "same-origin" 
    }).then(() => {
        window.location.href = "/login/";
    });
};


//----------------
// CHECKTBOX TEXT
//----------------
document.addEventListener('DOMContentLoaded', () => {
    const checkbox = document.getElementById('isActive');
    const text = document.getElementById('activeText');

    const toggleActiveText = () => {
        if (checkbox.checked) {
            text.textContent = 'Activo';
            text.classList.remove('text-danger');
            text.classList.add('text-success');
        } else {
            text.textContent = 'Inactivo';
            text.classList.remove('text-success');
            text.classList.add('text-danger');
        }
    };

    toggleActiveText(); // Inicializa el texto
    checkbox.addEventListener('change', toggleActiveText);
});


document.addEventListener('DOMContentLoaded', () => {
    const checkboxEdit = document.getElementById('isActiveedit');
    const textEdit = document.getElementById('activeTextedit');

    if (!checkboxEdit || !textEdit) return;

    const toggleActiveTextEdit = () => {
        if (checkboxEdit.checked) {
            textEdit.textContent = 'Activo';
            textEdit.classList.remove('text-danger');
            textEdit.classList.add('text-success');
        } else {
            textEdit.textContent = 'Inactivo';
            textEdit.classList.remove('text-success');
            textEdit.classList.add('text-danger');
        }
    };

    // Inicializar al cargar
    toggleActiveTextEdit();

    // Escuchar cambios
    checkboxEdit.addEventListener('change', toggleActiveTextEdit);
});
