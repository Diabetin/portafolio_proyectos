package com.example.galaxywatchcamerabridge

import android.content.Intent
import android.util.Log
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService

class WatchMessageReceiverService : WearableListenerService() {
    
    companion object {
        const val ACTION_START_CAMERA = "com.example.galaxywatchcamerabridge.START_CAMERA"
        const val ACTION_STOP_CAMERA = "com.example.galaxywatchcamerabridge.STOP_CAMERA"
        const val ACTION_CAPTURE = "com.example.galaxywatchcamerabridge.CAPTURE"
        const val ACTION_FLIP_CAMERA = "com.example.galaxywatchcamerabridge.FLIP_CAMERA"
        const val ACTION_SWITCH_MODE = "com.example.galaxywatchcamerabridge.SWITCH_MODE"
    }

    override fun onMessageReceived(messageEvent: MessageEvent) {
        super.onMessageReceived(messageEvent)
        val msg = "Recibido de reloj: ${messageEvent.path}"
        Log.d("WatchMessageReceiver", msg)
        AppLogger.log(msg)

        when (messageEvent.path) {
            "/camera_action/start" -> {
                val intent = Intent(this, CameraBridgeService::class.java).apply {
                    action = ACTION_START_CAMERA
                    putExtra("node_id", messageEvent.sourceNodeId)
                }
                startForegroundService(intent)
            }
            "/camera_action/stop" -> {
                val intent = Intent(this, CameraBridgeService::class.java).apply {
                    action = ACTION_STOP_CAMERA
                }
                startService(intent)
            }
            "/camera_action/capture" -> {
                val intent = Intent(this, CameraBridgeService::class.java).apply {
                    action = ACTION_CAPTURE
                }
                startService(intent)
            }
            "/camera_action/flip" -> {
                val intent = Intent(this, CameraBridgeService::class.java).apply {
                    action = ACTION_FLIP_CAMERA
                }
                startService(intent)
            }
            "/camera_action/switch_mode" -> {
                val intent = Intent(this, CameraBridgeService::class.java).apply {
                    action = ACTION_SWITCH_MODE
                }
                startService(intent)
            }
        }
    }
}
