package com.example.galaxywatchcamerabridge

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.net.wifi.p2p.WifiP2pGroup
import android.net.wifi.p2p.WifiP2pManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.provider.MediaStore
import android.util.Log
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.*
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.core.content.PermissionChecker
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.channels.Channel as CoroutineChannel
import kotlinx.coroutines.tasks.await
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraBridgeService : LifecycleService() {

    private val NOTIFICATION_ID = 101
    private val CHANNEL_ID = "CameraBridgeChannel"

    private var imageCapture: ImageCapture? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var recording: Recording? = null
    private lateinit var cameraExecutor: ExecutorService
    private var cameraProvider: ProcessCameraProvider? = null
    
    private var targetNodeId: String? = null
    private var currentLensFacing = CameraSelector.LENS_FACING_BACK
    private var isVideoMode = false
    private var lastFrameTime = 0L

    // Transmisión
    private var videoOutputStream: DataOutputStream? = null
    private val frameQueue = CoroutineChannel<ByteArray>(capacity = 2, onBufferOverflow = BufferOverflow.DROP_OLDEST)
    private var streamJob: Job? = null
    
    // Wi-Fi Direct
    private var wifiP2pManager: WifiP2pManager? = null
    private var wifiP2pChannel: WifiP2pManager.Channel? = null
    private var serverSocket: ServerSocket? = null
    private var clientSocket: Socket? = null
    
    private var isStartingConnection = false

    override fun onCreate() {
        super.onCreate()
        AppLogger.log("Servicio: Iniciado.")
        cameraExecutor = Executors.newSingleThreadExecutor()
        wifiP2pManager = getSystemService(WIFI_P2P_SERVICE) as? WifiP2pManager
        wifiP2pChannel = wifiP2pManager?.initialize(this, Looper.getMainLooper(), null)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            WatchMessageReceiverService.ACTION_START_CAMERA -> {
                if (isStartingConnection) {
                    AppLogger.log("START ignorado: Conexión en progreso.")
                    return START_NOT_STICKY
                }
                
                // Si ya hay algo activo, lo cerramos antes de empezar de cero
                if (clientSocket != null || videoOutputStream != null) {
                    AppLogger.log("Reiniciando conexión previa...")
                    closeVideoStream()
                }

                targetNodeId = intent.getStringExtra("node_id")
                startForeground(NOTIFICATION_ID, createNotification())
                cleanupAndStartWifi()
            }
            WatchMessageReceiverService.ACTION_STOP_CAMERA -> {
                AppLogger.log("STOP recibido.")
                stopSelf()
            }
            WatchMessageReceiverService.ACTION_CAPTURE -> {
                if (isVideoMode) toggleRecording() else takePhoto()
            }
            WatchMessageReceiverService.ACTION_FLIP_CAMERA -> {
                currentLensFacing = if (currentLensFacing == CameraSelector.LENS_FACING_BACK) CameraSelector.LENS_FACING_FRONT else CameraSelector.LENS_FACING_BACK
                startCamera()
            }
            WatchMessageReceiverService.ACTION_SWITCH_MODE -> {
                isVideoMode = !isVideoMode
                startCamera()
                sendStatusToWatch(if (isVideoMode) "MODE_VIDEO" else "MODE_PHOTO")
            }
        }
        return START_NOT_STICKY
    }

    private fun cleanupAndStartWifi() {
        val nodeId = targetNodeId ?: return
        isStartingConnection = true
        
        AppLogger.log("Wi-Fi: Limpiando red...")
        wifiP2pManager?.removeGroup(wifiP2pChannel, object : WifiP2pManager.ActionListener {
            override fun onSuccess() { createWifiGroup(nodeId) }
            override fun onFailure(reason: Int) { createWifiGroup(nodeId) }
        })
    }

    private fun createWifiGroup(nodeId: String) {
        AppLogger.log("Wi-Fi: Intentando crear grupo...")
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            AppLogger.log("Error: Sin permisos GPS. Fallback BT.")
            startBluetoothFallback(nodeId)
            return
        }

        wifiP2pManager?.createGroup(wifiP2pChannel, object : WifiP2pManager.ActionListener {
            override fun onSuccess() {
                AppLogger.log("Wi-Fi: Grupo creado. Obteniendo IP...")
                lifecycleScope.launch {
                    delay(2000) // Tiempo para que el hardware asigne la IP
                    requestWifiCredentials(nodeId)
                }
            }
            override fun onFailure(reason: Int) {
                AppLogger.log("Wi-Fi: Error createGroup ($reason). Fallback BT.")
                startBluetoothFallback(nodeId)
            }
        })
    }

    private fun requestWifiCredentials(nodeId: String) {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return
        
        wifiP2pManager?.requestGroupInfo(wifiP2pChannel) { group: WifiP2pGroup? ->
            if (group != null) {
                val ssid = group.networkName
                val pass = group.passphrase
                val ip = "192.168.49.1"
                
                AppLogger.log("RED -> SSID: $ssid | PW: $pass")
                
                val json = JSONObject().apply {
                    put("ssid", ssid)
                    put("password", pass)
                    put("ip", ip)
                }.toString()

                lifecycleScope.launch(Dispatchers.IO) {
                    try {
                        Wearable.getMessageClient(this@CameraBridgeService).sendMessage(nodeId, "/wifi_info", json.toByteArray()).await()
                        AppLogger.log("Wi-Fi: Credenciales enviadas al reloj.")
                        startTcpServer()
                    } catch (e: Exception) { 
                        AppLogger.log("Error envío BT. Fallback.")
                        startBluetoothFallback(nodeId)
                    }
                }
            } else {
                AppLogger.log("Error: Group Info NULL. Fallback BT.")
                startBluetoothFallback(nodeId)
            }
        }
    }

    private fun startTcpServer() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                serverSocket?.close()
                serverSocket = ServerSocket(8080).apply {
                    reuseAddress = true
                    soTimeout = 15000 // Timeout de 15 segundos en el socket directamente
                }
                
                AppLogger.log("TCP: Servidor activo (8080). Esperando...")
                
                clientSocket = serverSocket?.accept()
                
                AppLogger.log("TCP: ¡RELOJ CONECTADO!")
                videoOutputStream = DataOutputStream(clientSocket!!.getOutputStream())
                isStartingConnection = false
                startStreamingJob()
            } catch (e: Exception) {
                AppLogger.log("TCP: Fallo o Timeout (${e.message}). Usando BT.")
                startBluetoothFallback(targetNodeId ?: "")
            }
        }
    }

    private fun startBluetoothFallback(nodeId: String) {
        isStartingConnection = false
        if (nodeId.isEmpty()) return
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                AppLogger.log("BT: Abriendo canal de respaldo...")
                val channelClient = Wearable.getChannelClient(this@CameraBridgeService)
                val channel = channelClient.openChannel(nodeId, "/camera_stream").await()
                videoOutputStream = DataOutputStream(channelClient.getOutputStream(channel).await())
                AppLogger.log("BT: Canal abierto.")
                startStreamingJob()
            } catch (e: Exception) {
                AppLogger.log("BT: Fallo crítico. Cámara sola.")
                withContext(Dispatchers.Main) { startCamera() }
            }
        }
    }

    private fun startStreamingJob() {
        streamJob?.cancel()
        streamJob = lifecycleScope.launch(Dispatchers.IO) {
            // Sincronizamos el encendido de la cámara al hilo principal
            withContext(Dispatchers.Main) { startCamera() }
            
            val out = videoOutputStream ?: return@launch
            try {
                for (data in frameQueue) {
                    if (!isActive) break
                    out.writeInt(data.size)
                    out.write(data)
                    out.flush()
                }
            } catch (e: Exception) {
                AppLogger.log("Stream: Error de envío. Cerrando.")
                withContext(Dispatchers.Main) { closeVideoStream() }
                stopSelf()
            }
        }
    }

    private fun startCamera() {
        lifecycleScope.launch(Dispatchers.Main) {
            if (cameraProvider == null) {
                val future = ProcessCameraProvider.getInstance(this@CameraBridgeService)
                try {
                    cameraProvider = withContext(Dispatchers.IO) { future.get() }
                    bindCamera()
                } catch (e: Exception) { AppLogger.log("Camera: Error Provider $e") }
            } else bindCamera()
        }
    }

    private fun bindCamera() {
        val provider = cameraProvider ?: return
        try {
            val isWifi = clientSocket?.isConnected == true
            val res = if (isWifi) android.util.Size(1280, 720) else android.util.Size(480, 480)
            
            val strategy = androidx.camera.core.resolutionselector.ResolutionSelector.Builder()
                .setResolutionStrategy(androidx.camera.core.resolutionselector.ResolutionStrategy(res, androidx.camera.core.resolutionselector.ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                .build()

            val analyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setResolutionSelector(strategy)
                .build().also { it.setAnalyzer(cameraExecutor) { img -> processImage(img, isWifi) } }

            val selector = CameraSelector.Builder().requireLensFacing(currentLensFacing).build()
            
            provider.unbindAll()

            if (isVideoMode) {
                videoCapture = VideoCapture.withOutput(Recorder.Builder().setQualitySelector(QualitySelector.from(Quality.HIGHEST)).build())
                provider.bindToLifecycle(this, selector, analyzer, videoCapture)
            } else {
                imageCapture = ImageCapture.Builder().setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY).build()
                provider.bindToLifecycle(this, selector, analyzer, imageCapture)
            }
            AppLogger.log("Cámara: LISTA (${if (isWifi) "WiFi-HD" else "BT-SD"})")
        } catch (e: Exception) { AppLogger.log("Camera: Error Vincular $e") }
    }

    private fun processImage(image: ImageProxy, isWifi: Boolean) {
        val now = System.currentTimeMillis()
        if (now - lastFrameTime < (if (isWifi) 16 else 33)) { image.close(); return }
        lastFrameTime = now
        try {
            val bmp = image.toBitmap()
            val matrix = Matrix().apply { 
                postRotate(image.imageInfo.rotationDegrees.toFloat())
                if (currentLensFacing == CameraSelector.LENS_FACING_FRONT) postScale(-1f, 1f, bmp.width / 2f, bmp.height / 2f)
            }
            val rotated = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, matrix, true)
            val width = if (isWifi) 720 else 320
            val height = if (isWifi) 1280 else 320
            val scaled = Bitmap.createScaledBitmap(rotated, width, height, true)
            val stream = ByteArrayOutputStream()
            scaled.compress(Bitmap.CompressFormat.JPEG, if (isWifi) 60 else 30, stream)
            frameQueue.trySend(stream.toByteArray())
        } catch (e: Exception) {} finally { image.close() }
    }

    private fun closeVideoStream() {
        // MUY IMPORTANTE: Todo lo de CameraX y red en el hilo principal o IO controlado
        lifecycleScope.launch(Dispatchers.Main) {
            AppLogger.log("Limpiando recursos...")
            isStartingConnection = false
            streamJob?.cancel()
            streamJob = null
            
            withContext(Dispatchers.IO) {
                try { videoOutputStream?.close() } catch (e: Exception) {}
                videoOutputStream = null
                try { clientSocket?.close() } catch (e: Exception) {}
                clientSocket = null
                try { serverSocket?.close() } catch (e: Exception) {}
                serverSocket = null
            }
            
            wifiP2pManager?.removeGroup(wifiP2pChannel, null)
            cameraProvider?.unbindAll()
            AppLogger.log("Recursos liberados.")
        }
    }

    private fun sendStatusToWatch(s: String) {
        val node = targetNodeId ?: return
        lifecycleScope.launch(Dispatchers.IO) { try { Wearable.getMessageClient(this@CameraBridgeService).sendMessage(node, "/camera_status", s.toByteArray()).await() } catch (e: Exception) {} }
    }

    private fun takePhoto() {
        val cap = imageCapture ?: return
        AppLogger.log("Capturando foto...")
        val cv = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "GW_${System.currentTimeMillis()}.jpg")
            put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            if(Build.VERSION.SDK_INT > Build.VERSION_CODES.P) put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/GalaxyWatchCamera")
        }
        cap.takePicture(ImageCapture.OutputFileOptions.Builder(contentResolver, MediaStore.Images.Media.EXTERNAL_CONTENT_URI, cv).build(), ContextCompat.getMainExecutor(this), object : ImageCapture.OnImageSavedCallback {
            override fun onError(e: ImageCaptureException) { AppLogger.log("Error Foto: ${e.message}") }
            override fun onImageSaved(r: ImageCapture.OutputFileResults) {
                AppLogger.log("¡Foto Guardada!"); sendStatusToWatch("PHOTO_SAVED")
            }
        })
    }

    private fun toggleRecording() {
        val cap = this.videoCapture ?: return
        if (recording != null) { recording?.stop(); recording = null; sendStatusToWatch("REC_STOP"); AppLogger.log("Video stop."); return }
        AppLogger.log("Video start...")
        val cv = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "GWV_${System.currentTimeMillis()}.mp4")
            put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
            if (Build.VERSION.SDK_INT > Build.VERSION_CODES.P) put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/GalaxyWatchCamera")
        }
        var pending = cap.output.prepareRecording(this, MediaStoreOutputOptions.Builder(contentResolver, MediaStore.Video.Media.EXTERNAL_CONTENT_URI).setContentValues(cv).build())
        if (PermissionChecker.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PermissionChecker.PERMISSION_GRANTED) pending = pending.withAudioEnabled()
        recording = pending.start(ContextCompat.getMainExecutor(this)) { ev ->
            if (ev is VideoRecordEvent.Start) sendStatusToWatch("REC_START")
            else if (ev is VideoRecordEvent.Finalize) { AppLogger.log("¡Video Guardado!"); sendStatusToWatch("REC_STOP") }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val m = getSystemService(NotificationManager::class.java)
            m?.createNotificationChannel(NotificationChannel(CHANNEL_ID, "Camera Bridge", NotificationManager.IMPORTANCE_LOW))
        }
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID).setContentTitle("Cámara GW7").setContentText("Transmisión activa").setSmallIcon(android.R.drawable.ic_menu_camera).build()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        recording?.stop()
        closeVideoStream()
    }

    override fun onBind(intent: Intent): IBinder? {
        super.onBind(intent)
        return null
    }
}
