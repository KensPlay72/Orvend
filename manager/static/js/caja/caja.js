
//contiene los productos que se van a agregar a caja
let datos = [];
//contiene los datos del filtro de busqueda
let productos_dato = [];

let fila_descuento;

let total_m=0;

//evento de busqueda por codigo
document.getElementById('codigo_busqueda').addEventListener('keydown', function (event) {
    if (event.key == "Enter") {
        event.preventDefault();
        let codigo = document.getElementById('codigo_busqueda').value;

        productos(codigo);
    }
});


//determinar si existe el codigo o no.
function productos(codigo) {
    if (codigo === "" || !Number.isInteger(Number(codigo))) {
        return console.log('Codigo no valido');
    }

    let producto = datos.findIndex(p => p.codigo === codigo);

    if (producto === -1) {
        sin_codigo(codigo);
    }
    else {
        con_codigo(producto);
        tabla_detalle_total();
    }
}

//agregar producto si existe el codigo en la tabla
function con_codigo(i) {
    datos[i].cantidad += 1;
    datos[i].subtotal = datos[i].cantidad * datos[i].precio_venta;

    let tabla = document.getElementById('tablaProductos');
    let cantidad = tabla.rows[i + 1].cells[2].querySelector('.pre');
    let subtotal = tabla.rows[i + 1].cells[5];

    cantidad.textContent = datos[i].cantidad;
    subtotal.textContent = 'L. ' + datos[i].subtotal.toFixed(2);

    
}

//fecth de busqueda sin el codigo no esta en la tabla
async function sin_codigo(codigo) {
    await fetch(`/manager/busquedacodigo/${codigo}/`, {
        method: 'GET',
        headers: {

        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('error');
            }

            return response.json();
        })
        .then(data => {

            let producto = {
                id: data.id,
                codigo: data.codigo_sku,
                nombre: data.nombre,
                precio_venta: parseFloat(data.precio_venta),
                cantidad: 1,
                descuento: 0.00,
                subtotal: parseFloat(data.precio_venta)
            }
            datos.push(producto)

            tabla_codigo(data.codigo_sku, data.nombre, 1, parseFloat(data.precio_venta).toFixed(2), 0, parseFloat(data.precio_venta).toFixed(2));
        })
        .catch(error => {
            console.log(error);
        })
}

//busqueda por nombre
let busqueda = document.getElementById('busqueda');
let resultados = document.getElementById('resultadoBusquda');

//evitar el evento de submit.
busqueda.addEventListener('keydown', function (event) {
    if (event.key == "Enter") {
        event.preventDefault();
    }
});

//controlador para que cuando se escribe rapido cancele el fetch hasta que termine la escritura.
let controlador = null;

//evento de input para buscar los productos de la base de datos y agregarlo a la lista.
busqueda.addEventListener('input', function () {

    resultados.innerHTML = "";
    resultados.style.display = "none";

    const texto = busqueda.value.trim();

    if (texto.length < 2) return;

    if (controlador) {
        controlador.abort();
    }

    controlador = new AbortController();

    fetch(`/manager/busquedanombre/${texto}`, {
        method: 'GET',
        signal: controlador.signal
    })
        .then(response => {
            if (!response.ok) {
                throw new Error("Error en la petición");
            }
            return response.json();
        })
        .then(data => {

            productos_dato = [];
            resultados.innerHTML = "";

            if (data.length > 0) {

                resultados.style.display = 'block';

                data.forEach((p, index) => {

                    productos_dato.push(p);

                    const div = document.createElement('div');
                    div.className = 'item-resultado';
                    div.textContent = p.nombre;

                    div.addEventListener('click', () => {
                        seleccionarProducto(index);
                    });

                    resultados.appendChild(div);
                });

            } else {
                resultados.style.display = 'block';
                resultados.innerHTML = `
                <div class="item-resultado">
                    Sin resultados
                </div>
            `;
            }
        })
        .catch(error => {
            if (error.name !== "AbortError") {
                console.log(error);
            }
        });
});

//numero de indicie de producto seleccionado.
let codex = 0;

//funcion para agregar los datos seleccionados de busqueda por nombre al modal.
function seleccionarProducto(index) {
    codex = index;
    
    let codigo = document.getElementById('nCodigo');
    let nombre = document.getElementById('nNombre');
    let precio = document.getElementById('nPrecio');

    codigo.value = productos_dato[index].codigo_sku;
    nombre.value = productos_dato[index].nombre;
    precio.value = 'L. ' + productos_dato[index].precio_venta;


    const modal = new bootstrap.Modal(document.getElementById('modalagregar'));
    modal.show();
}

//evento de boton del modal agregar los datos seleccionados a la tabla y al arreglo de datos.
document.getElementById('btnregis').addEventListener('click', function (e) {
    e.preventDefault();

    let codigo = document.getElementById('nCodigo').value;

    let cantidad = document.getElementById('nCanitdad').value;

    if (cantidad.trim() === "") {
        return;
    }

    let producto = datos.findIndex(p => p.codigo === codigo);

    if (producto === -1) {
        let producto = {
            id: productos_dato[codex].id,
            codigo: productos_dato[codex].codigo_sku,
            nombre: productos_dato[codex].nombre,
            precio_venta: productos_dato[codex].precio_venta,
            cantidad: parseInt(cantidad),
            descuento: 0.00,
            subtotal: (productos_dato[codex].precio_venta * cantidad)
        }
        datos.push(producto)

        tabla_codigo(productos_dato[codex].codigo_sku, productos_dato[codex].nombre, parseInt(cantidad),
            productos_dato[codex].precio_venta, 0, parseFloat(productos_dato[codex].precio_venta * parseInt(cantidad)).toFixed(2));

        const modalEl = document.getElementById('modalagregar');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        modal.hide();

        document.getElementById('nCanitdad').value=0;

        tabla_detalle_total();

    }
    else {

        tabla_detalle_total();
    }

});

// cerrar selector
busqueda.addEventListener('blur', function () {
    setTimeout(() => {
        resultados.style.display = 'none';
    }, 300);
});

//abrir el selector de productos por nombre
busqueda.addEventListener('focus', function () {
    if (busqueda.value.length < 2) {
        resultados.innerHTML = '';
        resultados.style.display = 'block';
        resultados.innerHTML += `
                            <div class="item-resultado">
                                _______________________
                                      Sin Resultados
                            </div>`;
    }
    setTimeout(() => {
        resultados.style.display = 'block';
    }, 200);
});

//agregar producto tabla
function tabla_codigo(codigo, nombre, canti, sub, des, total) {
    let tabla = document.querySelector(`#tablaProductos tbody`);

    let fila = tabla.insertRow();

    fila.insertCell(0).textContent = codigo;
    fila.insertCell(1).textContent = nombre;
    let cantidad = fila.insertCell(2);
    fila.insertCell(3).textContent = 'L. ' + sub;
    fila.insertCell(4).textContent = 'L. ' + des + '.00';
    fila.insertCell(5).textContent = 'L. ' + total;

    let boton = fila.insertCell(6);

    let div_row = document.createElement('div');
    div_row.className = 'div_row';

    let div_pre = document.createElement('div');

    let p = document.createElement('p');
    p.className='pre';
    p.textContent=canti;

    div_pre.appendChild(p)

    let div_button_action = document.createElement('div');
    div_button_action.className = 'button_action';

    let button_mas = document.createElement('button');
    button_mas.classList.add = 'btn_add';
    button_mas.className = 'btn_add';
    button_mas.textContent = '+';

    let button_men = document.createElement('button');
    button_men.classList.add = 'btn_remove';
    button_men.className = 'btn_remove';
    button_men.textContent = '-';

    div_button_action.appendChild(button_mas);
    div_button_action.appendChild(button_men);

    div_row.appendChild(div_pre);
    div_row.appendChild(div_button_action);

    cantidad.appendChild(div_row);

    let div_descueto = document.createElement('div');
    div_descueto.className = 'button_action';

    let buton_descueto = document.createElement('button');
    buton_descueto.classList.add = 'btn_add';
    buton_descueto.className = 'btn_discunt';
    buton_descueto.textContent = 'descuento';

    div_descueto.appendChild(buton_descueto);

    boton.appendChild(div_descueto);
    tabla_detalle_total();
}

const tbody = document.querySelector("#tablaProductos tbody");

tbody.addEventListener("click", (e) => {

    const fila = e.target.closest("tr");

    if (e.target.classList.contains("btn_add")) {

        const fila = e.target.closest("tr");

        let indice = fila.sectionRowIndex;
        
        datos[indice].cantidad++;
        datos[indice].subtotal = datos[indice].cantidad * datos[indice].precio_venta;
        
        let c = fila.querySelector('.pre');
        let s = fila.cells[5];

        s.textContent = 'L. '+datos[indice].subtotal.toFixed(2);

        c.textContent = datos[indice].cantidad;

        tabla_detalle_total();
    }

    if(e.target.classList.contains('btn_remove')){
        const fila = e.target.closest('tr');
        let indice =fila.sectionRowIndex;
        
        datos[indice].cantidad--;
        datos[indice].subtotal = datos[indice].cantidad * datos[indice].precio_venta;
        
        if(datos[indice].cantidad===0){
            datos.splice(indice,1);
            fila.remove();
            tabla_detalle_total();
            return;
        }

        let c = fila.querySelector('.pre');
        let s = fila.cells[5];

        s.textContent = 'L. '+datos[indice].subtotal.toFixed(2);

        c.textContent = datos[indice].cantidad;

        tabla_detalle_total();
    }

    if(e.target.classList.contains('btn_discunt')){
        const fila = e.target.closest('tr');
        add_descuento(fila);
    }

});

function add_descuento(fila){
    fila_descuento=fila;
    let modal = new bootstrap.Modal(document.getElementById('modalDescuento'));
    modal.show(); 
}

document.getElementById('btndescuento').addEventListener('click',function(e){
    e.preventDefault();
    let descuento = document.getElementById('Ddescuento');
    let indice = fila_descuento.sectionRowIndex;

    datos[indice].descuento = parseFloat(descuento.value);

    let d=fila_descuento.cells[4]
    d.textContent = 'L. '+datos[indice].descuento.toFixed(2);

    fila_descuento=null;

    let modal = document.getElementById('modalDescuento');
    let modalE = bootstrap.Modal.getOrCreateInstance(modal);

    tabla_detalle_total();

    modalE.hide();

    modal.hide();

})

function tabla_detalle_total() {
    let subtotal = 0;
    let descuento = 0;

    datos.forEach((item, index) => {
        subtotal += item.subtotal;
        descuento += item.descuento;
    })


    let impuesto = subtotal * 0.15;
    let total = (subtotal + impuesto) - descuento;

    let tabla = document.getElementById('detalle-total');
    let celda_subtotal = tabla.rows[0].cells[1];
    let celda_descuento = tabla.rows[1].cells[1];
    let celda_impusto = tabla.rows[2].cells[1];
    let celda_total = tabla.rows[3].cells[1];

    total_m=total;

    celda_subtotal.textContent = 'L. ' + subtotal.toFixed(2);
    celda_descuento.textContent = 'L. ' + descuento.toFixed(2);
    celda_impusto.textContent = 'L. ' + impuesto.toFixed(2);
    celda_total.textContent = 'L. ' + total.toFixed(2);
}


//pagos

document.getElementById('Pagar').addEventListener('click',function(e){
    let modal = new bootstrap.Modal(document.getElementById('modalPago'));
    modal.show();
});

document.getElementById('tipo_pago').addEventListener('change',function(e){

    let opcion = e.target.value;
    let dinero = document.getElementById('div_dinero');
    let numero = document.getElementById('div_nuemro');
    let digito = document.getElementById('div_digito');
    let banco = document.getElementById('div_banco');
    let red =document.getElementById('div_red');

    if(opcion==="pago_contado"){
        dinero.style.display='block';
        numero.style.display='none';
        digito.style.display='none';
        banco.style.display='none';
        red.style.display='none';
    }
    else if(opcion==="pago_tarjeta"){
        dinero.style.display='none';
        numero.style.display='block';
        digito.style.display='block';
        banco.style.display='block';
        red.style.display='block';
    }
    else{
        dinero.style.display='none';
        numero.style.display='none';
        digito.style.display='none';
        banco.style.display='none';
        red.style.display='none';
    }
});

