package com.example.galaxywatchcamerabridge

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var statusTextView: TextView
    private lateinit var logTextView: TextView

    private val requiredPermissions = mutableListOf(
        Manifest.permission.CAMERA,
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.ACCESS_FINE_LOCATION
    ).apply {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
            add(Manifest.permission.NEARBY_WIFI_DEVICES)
        }
    }.toTypedArray()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        updateStatus(allGranted)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 60, 40, 40)
        }

        statusTextView = TextView(this).apply {
            textSize = 18f
            setPadding(0, 0, 0, 40)
        }

        logTextView = TextView(this).apply {
            textSize = 12f
            typeface = Typeface.MONOSPACE
        }

        val scrollView = ScrollView(this).apply {
            addView(logTextView)
        }

        layout.addView(statusTextView)
        layout.addView(scrollView)
        setContentView(layout)

        lifecycleScope.launch {
            AppLogger.logs.collect { logs ->
                logTextView.text = "--- LOGS DE SISTEMA ---\n\n" + logs.joinToString("\n")
            }
        }

        if (hasPermissions()) {
            updateStatus(true)
        } else {
            permissionLauncher.launch(requiredPermissions)
        }
    }

    private fun hasPermissions(): Boolean {
        return requiredPermissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun updateStatus(granted: Boolean) {
        if (granted) {
            statusTextView.text = "✅ Todo configurado.\n\nPuedes cerrar esta app. Cuando abras la app en tu Galaxy Watch 7, la cámara se activará automáticamente."
        } else {
            statusTextView.text = "❌ Faltan permisos de Cámara, Micrófono o Notificaciones para funcionar."
        }
    }
}
