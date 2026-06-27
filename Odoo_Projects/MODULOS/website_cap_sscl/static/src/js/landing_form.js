document.addEventListener("DOMContentLoaded", function() {
  console.log("Landing form script loaded");
  let datosPerfil = {
    renta: null,
    ahorro: null,
    situacion: null
  };
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
  var nextBtn = document.getElementById("nextBtn");
  var step1 = document.getElementById("step1");
  var step2 = document.getElementById("step2");
  if (nextBtn && step1 && step2) {
    nextBtn.addEventListener("click", function() {
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
      step1.style.display = "none";
      step2.style.display = "block";
      setTimeout(function(){
        var firstBtn = step2.querySelector('.option-btn');
        if(firstBtn) firstBtn.focus();
      }, 150);
    });
  } else {
    console.error("Step navigation elements not found");
  }
  var btnLlamen = document.getElementById("btnQuieroLlamen");
  if (btnLlamen) {
    btnLlamen.addEventListener('click', function() {
      var form = document.getElementById('landingForm');
      var nombre = form.querySelector('[name="nombre"]').value.trim();
      var apellido = form.querySelector('[name="apellido"]').value.trim();
      var telefono = form.querySelector('[name="telefono"]').value.trim();
      var email = form.querySelector('[name="email"]').value.trim();
      if (!datosPerfil.renta || !datosPerfil.ahorro || !datosPerfil.situacion) {
        alert("Por favor, responde todas las preguntas antes de enviar tus datos.");
        return;
      }
      btnLlamen.disabled = true;
      btnLlamen.textContent = "Enviando...";
      var requestData = {
        jsonrpc: "2.0",
        method: "call",
        params: {
          nombre: nombre,
          apellido: apellido,
          telefono: telefono,
          email: email,
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
          btnLlamen.disabled = false;
          btnLlamen.textContent = "Quiero que me llamen";
          var result = data.result || data;
          if (result && result.success) {
            // Mostrar el popup de confirmación
            var popupConfirm = document.getElementById('popupConfirm');
            if (popupConfirm) {
              popupConfirm.style.display = "flex";
              setTimeout(function(){
                window.location.href = "/landing"; // Cambia a la URL que desees para redirigir después
              }, 2750);
            }
            step2.style.display = "none";
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
        } catch (parseError) {
          console.error("JSON parse error:", parseError);
          console.error("Raw response was:", textData);
          btnLlamen.disabled = false;
          btnLlamen.textContent = "Quiero que me llamen";
          alert("Error al procesar la respuesta del servidor.");
        }
      })
      .catch(function(err) {
        console.error('Fetch error:', err);
        btnLlamen.disabled = false;
        btnLlamen.textContent = "Quiero que me llamen";
        alert("Ocurrió un error de red. Intenta nuevamente.");
      });
    });
  } else {
    console.error("Submit button not found");
  }
  // Validaciones en vivo para email y teléfono
  var emailInput = document.querySelector('[name="email"]');
  if (emailInput) {
    emailInput.addEventListener('blur', function() {
      var email = this.value.trim();
      var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      this.style.borderBottomColor = (email && !emailRegex.test(email)) ? '#ff4444' : '#0056d2';
    });
  }
  var telefonoInput = document.querySelector('[name="telefono"]');
  if (telefonoInput) {
    telefonoInput.addEventListener('blur', function() {
      var telefono = this.value.trim();
      this.style.borderBottomColor = (telefono && telefono.length < 8) ? '#ff4444' : '#0056d2';
    });
  }
  console.log("Landing form script initialization complete");
});
