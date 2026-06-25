document.addEventListener("DOMContentLoaded", function () {
  const btn = document.getElementById("btn-logout-caja");

  if (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      let modal= new bootstrap.Modal(document.getElementById('modalCierre'));
      modal.show();
      
    });
  }
});


document.getElementById("postcierre").addEventListener("submit",function(e){
  e.preventDefault();
  Swal.fire({
        title: "¿Cerrar sesión?",
        text: "Tu sesión se cerrará y tendrás que iniciar sesión nuevamente.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Sí, cerrar sesión",
        cancelButtonText: "Cancelar",
        confirmButtonColor: "#d33", // rojo
        cancelButtonColor: "#6c757d", // gris
      }).then((result) => {
        if (result.isConfirmed) {
          guargar_turno()
        }
      });
  
});

function guargar_turno(){
  
  let data={
    efectio_encaja: parseFloat(document.getElementById("efectivo_cierre").value)
  }

  fetch("/manager/cierre_caja/",{
    method:"POST",
    headers:{
      "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body:JSON.stringify(data)
  })
  .then(async response=>{
        if (!response.ok){
            const dato = await response.json();
                console.log(dato)
                throw new Error(
                dato.error || dato.message || "Error desconocido"
                );
        }
        return response.json();
  })
  .then(data=>{
    cerrar_sesion()
  })
  .catch(error=>{
    mensaje(error.message,"error","");  
  })
}

function cerrar_sesion(){
          fetch("/accounts/logout/", {
            method: "POST",
            headers: {
              "X-CSRFToken": getCookie("csrftoken"),
            },
          })
            .then(() => {
              window.location.href = "/accounts/login/";
            })
            .catch((error) => {
              console.error("Error logout:", error);
              window.location.href = "/accounts/login/";
            });
}

function mensaje(mensaje,tipo,funcion){
    Swal.fire({
        title:mensaje,
        icon:tipo,
        confirmButtonText:"Aceptar",
        customClass: { confirmButton: "classbotones" }
    }).then(()=>{
        if(typeof funcion==="function"){
            funcion();
        }
    })
}