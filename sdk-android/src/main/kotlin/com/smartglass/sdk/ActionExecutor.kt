package com.smartglass.sdk

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.widget.Toast
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat

object ActionExecutor {
    private const val CHANNEL_ID = "smartglass_actions"

    fun execute(actions: List<Action>, context: Context) {
        actions.forEach { action ->
            when (action.type.uppercase()) {
                "NAVIGATE" -> handleNavigate(action.payload, context)
                "SHOW_TEXT" -> handleShowText(action.payload, context)
                else -> Unit
            }
        }
    }

    private fun handleNavigate(payload: Map<String, Any>, context: Context) {
        val destination = payload["destination"] as? String
        if (destination.isNullOrBlank()) return

        val geoUri = Uri.parse("geo:0,0?q=${Uri.encode(destination)}")
        val mapsIntent = Intent(Intent.ACTION_VIEW, geoUri).apply {
            setPackage("com.google.android.apps.maps")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }

        when {
            mapsIntent.resolveActivity(context.packageManager) != null -> context.startActivity(mapsIntent)
            else -> {
                val genericIntent = Intent(Intent.ACTION_VIEW, geoUri).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                if (genericIntent.resolveActivity(context.packageManager) != null) {
                    context.startActivity(genericIntent)
                }
            }
        }
    }

    private fun handleShowText(payload: Map<String, Any>, context: Context) {
        val message = payload["message"] as? String
        if (message.isNullOrBlank()) return

        Toast.makeText(context.applicationContext, message, Toast.LENGTH_LONG).show()

        createNotificationChannel(context)
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("SmartGlass")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        NotificationManagerCompat.from(context).notify(message.hashCode(), notification)
    }

    private fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "SmartGlass Actions",
                NotificationManager.IMPORTANCE_DEFAULT,
            )

            val notificationManager =
                context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}
