package com.example.galaxywatchcamerabridge

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object AppLogger {
    val logs = MutableStateFlow<List<String>>(emptyList())

    fun log(message: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val entry = "[$time] $message"
        logs.update { current ->
            val newList = current.toMutableList()
            newList.add(0, entry)
            if (newList.size > 50) newList.removeAt(newList.lastIndex)
            newList
        }
    }
}
