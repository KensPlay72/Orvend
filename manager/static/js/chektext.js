
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