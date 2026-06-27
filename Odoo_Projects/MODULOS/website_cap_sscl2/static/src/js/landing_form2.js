/**
 * landing_form2.js (MODIFICADO PARA FLUJO 3 PASOS Y POPUP CONFIRMACIÓN)
 * Primer paso datos personales, luego perfil financiero, luego fecha y enviar.
 */
document.addEventListener("DOMContentLoaded", function() {
  let datosPerfil = { renta: null, ahorro: null, situacion: null };
  // Marcado visual y almacenamiento de opciones (perfil financiero)
  document.querySelectorAll('.option-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var grupo = btn.getAttribute('data-name');
      document.querySelectorAll('.option-btn[data-name="'+grupo+'"]').forEach(function(x){
        x.classList.remove('selected');
      });
      btn.classList.add('selected');
      datosPerfil[grupo] = btn.getAttribute('data-value');
    });
  });
  // Paso 1 -> Paso 2
  var nextBtnStep1 = document.getElementById("nextBtnStep1");
  var step1 = document.getElementById("step1");
  var step2 = document.getElementById("step2");
  var step3 = document.getElementById("step3");
  // Validaciones de los campos de contacto
  if (nextBtnStep1 && step1 && step2) {
    nextBtnStep1.addEventListener("click", function() {
      var nombre = step1.querySelector('[name="nombre"]').value.trim();
      var apellido = step1.querySelector('[name="apellido"]').value.trim();
      var telefono = step1.querySelector('[name="telefono"]').value.trim();
      var email = step1.querySelector('[name="email"]').value.trim();
      if (!nombre || !apellido || !telefono || !email) {
        alert("Por favor, completa todos los campos antes de continuar.");
        return;
      }
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        alert("Por favor, ingresa un email válido.");
        return;
      }
      if (telefono.length < 8) {
        alert("Por favor, ingresa un teléfono válido.");
        return;
      }
      // Mostrar paso 2
      step1.style.display = "none";
      step2.style.display = "block";
      setTimeout(function(){
        var firstBtn = step2.querySelector('.option-btn');
        if(firstBtn) firstBtn.focus();
      }, 120);
    });
  } else {
    console.error("[landing_form2] step1/step2 elements not found");
  }
  // Paso 2 -> Paso 3
  var nextBtnStep2 = document.getElementById("nextBtnStep2");
  if (nextBtnStep2 && step2 && step3) {
    nextBtnStep2.addEventListener("click", function() {
      if (!datosPerfil.renta || !datosPerfil.ahorro || !datosPerfil.situacion) {
        alert("Por favor, responde todas las preguntas antes de continuar.");
        return;
      }
      step2.style.display = "none";
      step3.style.display = "block";
      setTimeout(function(){
        var dateInput = step3.querySelector('input[name="fecha_agenda"]');
        if(dateInput) dateInput.focus();
      }, 120);
      // Set min date apenas llegamos al paso 3
      var dateInput = step3.querySelector('input[name="fecha_agenda"]');
      if (dateInput) {
        var tzOffsetMs = new Date().getTimezoneOffset() * 60 * 1000;
        var today = new Date(Date.now() - tzOffsetMs).toISOString().slice(0,10);
        dateInput.setAttribute('min', today);
      }
    });
  } else {
    console.error("[landing_form2] step2/step3 elements not found");
  }
  // Envío final del formulario
  var form = document.getElementById('landingForm');
  var submitBtn = document.getElementById('submitBtn');
  if (form && submitBtn && step3 && step2 && step1) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      // Campos personales (del paso 1)
      var nombre = form.querySelector('[name="nombre"]').value.trim();
      var apellido = form.querySelector('[name="apellido"]').value.trim();
      var telefono = form.querySelector('[name="telefono"]').value.trim();
      var email = form.querySelector('[name="email"]').value.trim();
      // Perfil (del paso 2)
      // Fecha (del paso 3)
      var fechaAgenda = form.querySelector('[name="fecha_agenda"]').value;
      // Validación de fecha
      if (!fechaAgenda) {
        alert("Por favor, selecciona una fecha de agendamiento.");
        return;
      }
      try {
        var sel = new Date(fechaAgenda + "T00:00:00");
        var today = new Date(); today.setHours(0,0,0,0);
        if (sel < today) {
          alert("La fecha de agendamiento debe ser hoy o una fecha futura.");
          return;
        }
      } catch (e) {
        alert("Selecciona una fecha de agendamiento válida.");
        return;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = "Enviando...";
      var requestData = {
        jsonrpc: "2.0",
        method: "call",
        params: {
          nombre: nombre,
          apellido: apellido,
          telefono: telefono,
          email: email,
          fecha_agenda: fechaAgenda,
          renta: datosPerfil.renta,
          ahorro: datosPerfil.ahorro,
          situacion: datosPerfil.situacion
        },
        id: Math.floor(Math.random() * 1000000)
      };
      fetch("/custom_web_lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData)
      })
      .then(function(response) {
        if (!response.ok) throw new Error('Network response was not ok: ' + response.status);
        return response.text();
      })
      .then(function(textData) {
        try {
          var data = JSON.parse(textData);
          var result = data.result || data;
          submitBtn.disabled = false;
          submitBtn.textContent = "Enviar";
          if (result && result.success) {
            // Mostrar el pop up centrado en vez de alert
            var popupConfirm = document.getElementById('popupConfirm');
            if (popupConfirm) {
              popupConfirm.style.display = "flex";
              setTimeout(function(){
                window.location.href = "/landing_form2"; // Cambia la URL si quieres redirigir a otro lugar
              }, 2750);
            }
            // Resetear formulario y pasos
            step3.style.display = "none";
            step1.style.display = "block";
            form.reset();
            document.querySelectorAll('.option-btn.selected').forEach(x=>x.classList.remove('selected'));
            datosPerfil = {renta:null, ahorro:null, situacion:null};
            return;
          } else {
            var errorMsg = (result && result.error) || 'Error desconocido';
            alert("Ocurrió un error al guardar tus datos: " + errorMsg);
            console.error("Server error:", errorMsg);
          }
        } catch (e) {
          console.error("JSON parse error:", e, textData);
          submitBtn.disabled = false;
          submitBtn.textContent = "Enviar";
          alert("Error al procesar la respuesta del servidor.");
        }
      })
      .catch(function(err) {
        console.error('Fetch error:', err);
        submitBtn.disabled = false;
        submitBtn.textContent = "Enviar";
        alert("Ocurrió un error de red. Intenta nuevamente.");
      });
    });
  } else {
    console.error("[landing_form2] submit button or form not found");
  }
  // Validaciones en blur (email y teléfono)
  var emailInput = document.querySelector('[name="email"]');
  if (emailInput) {
    emailInput.addEventListener('blur', function() {
      var email = this.value.trim();
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      this.style.borderColor = (email && !emailRegex.test(email)) ? '#ff4444' : '#e5e7eb';
    });
  }
  var telefonoInput = document.querySelector('[name="telefono"]');
  if (telefonoInput) {
    telefonoInput.addEventListener('blur', function() {
      var telefono = this.value.trim();
      this.style.borderColor = (telefono && telefono.length < 8) ? '#ff4444' : '#e5e7eb';
    });
  }
});
