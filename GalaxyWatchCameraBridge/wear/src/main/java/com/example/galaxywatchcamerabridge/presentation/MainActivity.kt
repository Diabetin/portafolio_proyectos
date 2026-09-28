package com.example.galaxywatchcamerabridge.presentation

import android.Manifest
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaActionSound
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSpecifier
import android.os.Bundle
import android.os.PowerManager
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import androidx.wear.compose.material.*
import com.google.android.gms.wearable.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.DataInputStream
import java.net.Socket

class MainActivity : ComponentActivity(), MessageClient.OnMessageReceivedListener {

    private val TAG = "WatchMainActivity"
    private var connectedPhoneNodeId by mutableStateOf<String?>(null)
    private var currentFrame by mutableStateOf<Bitmap?>(null)
    private val mediaActionSound = MediaActionSound()
    private var cameraMode by mutableStateOf("MODE_PHOTO")
    private var isRecording by mutableStateOf(false)
    
    private var isStreaming = false
    private var videoSocket: Socket? = null
    private var connectivityManager: ConnectivityManager? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    private val channelCallback = object : ChannelClient.ChannelCallback() {
        override fun onChannelOpened(channel: ChannelClient.Channel) {
            Log.d(TAG, "Canal abierto: ${channel.path}")
            sendLogToPhone("Canal BT abierto: ${channel.path}")
            if (channel.path == "/camera_stream") startReadingStream(channel)
        }
    }

    private fun sendLogToPhone(msg: String) {
        val node = connectedPhoneNodeId ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            try { 
                Wearable.getMessageClient(this@MainActivity).sendMessage(node, "/camera_action/watch_log", msg.toByteArray()).await() 
            } catch (e: Exception) {}
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mediaActionSound.load(MediaActionSound.SHUTTER_CLICK)
        mediaActionSound.load(MediaActionSound.START_VIDEO_RECORDING)
        mediaActionSound.load(MediaActionSound.STOP_VIDEO_RECORDING)

        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(PowerManager.SCREEN_BRIGHT_WAKE_LOCK, "CameraBridge:WakeLock")
        
        val wifiManager = getSystemService(Context.WIFI_SERVICE) as WifiManager
        wifiLock = wifiManager.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "CameraBridge:WifiLock")

        permissionLauncher.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.NEARBY_WIFI_DEVICES))

        setContent {
            var isConnecting by remember { mutableStateOf(false) }

            WatchCameraScreen(
                frame = currentFrame,
                isConnected = connectedPhoneNodeId != null,
                isConnecting = isConnecting,
                cameraMode = cameraMode,
                isRecording = isRecording,
                onConnectClick = {
                    isConnecting = true
                    detectPhoneAndStartCamera()
                },
                onCaptureClick = { 
                    if (cameraMode == "MODE_PHOTO") mediaActionSound.play(MediaActionSound.SHUTTER_CLICK)
                    else mediaActionSound.play(if (isRecording) MediaActionSound.STOP_VIDEO_RECORDING else MediaActionSound.START_VIDEO_RECORDING)
                    sendActionToPhone("/camera_action/capture") 
                },
                onFlipClick = { sendActionToPhone("/camera_action/flip") },
                onSwitchModeClick = { sendActionToPhone("/camera_action/switch_mode") }
            )
        }
    }

    private fun connectToWifi(ssid: String, pass: String, ip: String) {
        val msg = "Intentando conectar Wi-Fi: $ssid"
        Log.d(TAG, msg)
        sendLogToPhone(msg)
        try {
            // Aseguramos que el callback anterior se desregistre para evitar crashes por múltiples solicitudes
            networkCallback?.let { 
                try { connectivityManager?.unregisterNetworkCallback(it) } catch (e: Exception) {}
            }
            
            // Para setSsid() algunas versiones de Android exigen que el SSID esté entre comillas dobles
            val quotedSsid = if (ssid.startsWith("\"") && ssid.endsWith("\"")) ssid else "\"$ssid\""
            sendLogToPhone("SSID formateado: $quotedSsid")
            
            val specifier = WifiNetworkSpecifier.Builder()
                .setSsid(quotedSsid)
                .setWpa2Passphrase(pass)
                .build()
                
            val request = NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .setNetworkSpecifier(specifier).build()

            connectivityManager = getSystemService(ConnectivityManager::class.java)
            networkCallback = object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    val availMsg = "Wi-Fi Disponible. Enlazando a $ip..."
                    Log.d(TAG, availMsg)
                    sendLogToPhone(availMsg)
                    connectivityManager?.bindProcessToNetwork(network)
                    startReadingSocket(ip)
                }
                override fun onUnavailable() {
                    val unavailMsg = "Wi-Fi No disponible."
                    Log.e(TAG, unavailMsg)
                    sendLogToPhone(unavailMsg)
                }
            }
            connectivityManager?.requestNetwork(request, networkCallback!!)
            sendLogToPhone("requestNetwork ejecutado. Esperando onAvailable...")
        } catch (e: Exception) {
            val errMsg = "Error en connectToWifi: $e"
            Log.e(TAG, errMsg)
            sendLogToPhone(errMsg)
        }
    }

    private fun startReadingSocket(ip: String) {
        if (isStreaming) return
        isStreaming = true
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val msg = "Abriendo Socket TCP a $ip..."
                Log.d(TAG, msg)
                sendLogToPhone(msg)
                videoSocket = Socket(ip, 8080)
                val dis = DataInputStream(videoSocket!!.getInputStream())
                val succMsg = "Socket Conectado. Leyendo frames..."
                Log.d(TAG, succMsg)
                sendLogToPhone(succMsg)
                while (isStreaming) {
                    val size = dis.readInt()
                    if (size in 1..5_000_000) {
                        val bytes = ByteArray(size)
                        dis.readFully(bytes)
                        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        if (bitmap != null) withContext(Dispatchers.Main) { currentFrame = bitmap }
                    } else break
                }
            } catch (e: Exception) { 
                val errMsg = "Error Socket: $e"
                Log.e(TAG, errMsg)
                sendLogToPhone(errMsg)
                isStreaming = false 
            }
        }
    }

    private fun startReadingStream(channel: ChannelClient.Channel) {
        if (isStreaming) return
        isStreaming = true
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                Log.d(TAG, "Leyendo de Channel BT...")
                val dis = DataInputStream(Wearable.getChannelClient(this@MainActivity).getInputStream(channel).await())
                while (isStreaming) {
                    val size = dis.readInt()
                    if (size in 1..5_000_000) {
                        val bytes = ByteArray(size)
                        dis.readFully(bytes)
                        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                        if (bitmap != null) withContext(Dispatchers.Main) { currentFrame = bitmap }
                    } else break
                }
            } catch (e: Exception) { 
                Log.e(TAG, "Error Channel BT: $e")
                isStreaming = false 
            }
        }
    }

    override fun onResume() {
        super.onResume()
        wakeLock?.acquire(10 * 60 * 1000L /*10 minutes*/)
        wifiLock?.acquire()
        Wearable.getMessageClient(this).addListener(this)
        Wearable.getChannelClient(this).registerChannelCallback(channelCallback)
        // detectPhoneAndStartCamera() -> Now handled by 'Conectar' button
    }

    override fun onPause() {
        super.onPause()
        Log.d(TAG, "onPause: (No limpiamos conexiones para evitar cortar el diálogo de Wi-Fi)")
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "onDestroy: Limpiando conexiones...")
        if (wakeLock?.isHeld == true) wakeLock?.release()
        if (wifiLock?.isHeld == true) wifiLock?.release()
        
        sendActionToPhone("/camera_action/stop")
        Wearable.getMessageClient(this).removeListener(this)
        Wearable.getChannelClient(this).unregisterChannelCallback(channelCallback)
        
        isStreaming = false
        try { videoSocket?.close() } catch (e: Exception) {}
        videoSocket = null
        
        networkCallback?.let { 
            try { connectivityManager?.unregisterNetworkCallback(it) } catch (e: Exception) {}
        }
        networkCallback = null
        connectivityManager?.bindProcessToNetwork(null)
        currentFrame = null
        mediaActionSound.release()
    }
    
    override fun onMessageReceived(event: MessageEvent) {
        Log.d(TAG, "Mensaje recibido: ${event.path}")
        when (event.path) {
            "/wifi_info" -> {
                val json = JSONObject(String(event.data))
                connectToWifi(json.getString("ssid"), json.getString("password"), json.getString("ip"))
            }
            "/camera_status" -> {
                val status = String(event.data)
                lifecycleScope.launch(Dispatchers.Main) {
                    when (status) {
                        "MODE_PHOTO" -> cameraMode = "MODE_PHOTO"
                        "MODE_VIDEO" -> cameraMode = "MODE_VIDEO"
                        "REC_START" -> isRecording = true
                        "REC_STOP" -> isRecording = false
                    }
                }
            }
        }
    }

    private fun detectPhoneAndStartCamera() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val nodes = Wearable.getNodeClient(this@MainActivity).connectedNodes.await()
                connectedPhoneNodeId = nodes.firstOrNull()?.id
                Log.d(TAG, "Nodo detectado: $connectedPhoneNodeId")
                if (connectedPhoneNodeId != null) sendActionToPhone("/camera_action/start")
            } catch (e: Exception) {
                Log.e(TAG, "Error detectando nodos: $e")
            }
        }
    }

    private fun sendActionToPhone(path: String) {
        val node = connectedPhoneNodeId ?: return
        lifecycleScope.launch(Dispatchers.IO) {
            try { 
                Log.d(TAG, "Enviando a teléfono: $path")
                Wearable.getMessageClient(this@MainActivity).sendMessage(node, path, byteArrayOf()).await() 
            } catch (e: Exception) {
                Log.e(TAG, "Error enviando $path: $e")
            }
        }
    }
}

@Composable
fun WatchCameraScreen(frame: Bitmap?, isConnected: Boolean, isConnecting: Boolean, cameraMode: String, isRecording: Boolean, onConnectClick: () -> Unit, onCaptureClick: () -> Unit, onFlipClick: () -> Unit, onSwitchModeClick: () -> Unit) {
    val haptic = LocalHapticFeedback.current
    var showFlash by remember { mutableStateOf(false) }
    LaunchedEffect(showFlash) { if (showFlash) { kotlinx.coroutines.delay(100); showFlash = false } }

    Scaffold(timeText = { TimeText() }) {
        Box(modifier = Modifier.fillMaxSize().background(Color.Black), contentAlignment = Alignment.Center) {
            if (frame != null) {
                Image(bitmap = frame.asImageBitmap(), contentDescription = "Stream", modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                AnimatedVisibility(visible = showFlash, enter = fadeIn(), exit = fadeOut(), modifier = Modifier.fillMaxSize()) {
                    Box(modifier = Modifier.fillMaxSize().background(Color.White.copy(alpha = 0.8f)))
                }
                if (isRecording) {
                    Row(modifier = Modifier.align(Alignment.TopCenter).padding(top = 24.dp).background(Color.Black.copy(alpha = 0.5f), shape = RoundedCornerShape(8.dp)).padding(horizontal = 8.dp, vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(modifier = Modifier.size(8.dp).background(Color.Red, CircleShape))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("REC", color = Color.White, style = MaterialTheme.typography.caption2)
                    }
                }
                Row(modifier = Modifier.fillMaxWidth().align(Alignment.BottomCenter).padding(bottom = 24.dp), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                    Button(onClick = { haptic.performHapticFeedback(HapticFeedbackType.LongPress); onSwitchModeClick() }, colors = ButtonDefaults.buttonColors(backgroundColor = Color.DarkGray.copy(alpha = 0.6f)), shape = CircleShape, modifier = Modifier.size(36.dp)) {
                        Text(if (cameraMode == "MODE_VIDEO") "🎥" else "📷", color = Color.White)
                    }
                    val interactionSource = remember { MutableInteractionSource() }
                    val isPressed by interactionSource.collectIsPressedAsState()
                    val scale by animateFloatAsState(if (isPressed) 0.8f else 1f)
                    Button(onClick = { haptic.performHapticFeedback(HapticFeedbackType.LongPress); if (cameraMode == "MODE_PHOTO") showFlash = true; onCaptureClick() }, interactionSource = interactionSource, colors = ButtonDefaults.buttonColors(backgroundColor = Color.White), shape = CircleShape, modifier = Modifier.size(46.dp).scale(scale)) {
                        if (isRecording) Box(modifier = Modifier.size(16.dp).background(Color.Red, RoundedCornerShape(2.dp)))
                        else Box(modifier = Modifier.size(36.dp).background(Color.Red, CircleShape))
                    }
                    Button(onClick = { haptic.performHapticFeedback(HapticFeedbackType.LongPress); onFlipClick() }, colors = ButtonDefaults.buttonColors(backgroundColor = Color.DarkGray.copy(alpha = 0.6f)), shape = CircleShape, modifier = Modifier.size(36.dp)) {
                        Text("🔄", color = Color.White)
                    }
                }
            } else {
                if (!isConnecting) {
                    Button(onClick = { haptic.performHapticFeedback(HapticFeedbackType.LongPress); onConnectClick() }, colors = ButtonDefaults.buttonColors(backgroundColor = Color.DarkGray)) {
                        Text("Conectar", color = Color.White)
                    }
                } else {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                        CircularProgressIndicator(indicatorColor = Color.Red)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = if (isConnected) "Conectando..." else "Buscando teléfono...", color = Color.White)
                    }
                }
            }
        }
    }
}
