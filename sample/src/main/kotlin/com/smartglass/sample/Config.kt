package com.smartglass.sample

import android.content.Context
import android.content.SharedPreferences

/**
 * Configuration manager for SmartGlass sample app.
 * 
 * Manages persistent settings such as backend server URL using SharedPreferences.
 * 
 * Usage:
 * ```kotlin
 * val config = Config(context)
 * config.backendUrl = "http://192.168.1.100:5000"
 * val url = config.backendUrl
 * ```
 */
class Config(context: Context) {
    
    companion object {
        private const val PREFS_NAME = "smartglass_config"
        private const val KEY_BACKEND_URL = "backend_url"
        private const val DEFAULT_BACKEND_URL = "http://localhost:5000"
    }
    
    private val prefs: SharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    
    /**
     * Backend server URL for API calls.
     * 
     * Default: http://localhost:5000
     * 
     * Examples:
     * - Local: http://localhost:5000
     * - Network: http://192.168.1.100:5000
     * - Production: https://api.smartglass.ai
     */
    var backendUrl: String
        get() = prefs.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL) ?: DEFAULT_BACKEND_URL
        set(value) {
            prefs.edit().putString(KEY_BACKEND_URL, value.trim()).apply()
        }
    
    /**
     * Reset to default configuration.
     */
    fun reset() {
        prefs.edit().clear().apply()
    }
    
    /**
     * Validate backend URL format.
     * 
     * @param url URL to validate
     * @return true if valid, false otherwise
     */
    fun isValidBackendUrl(url: String): Boolean {
        val trimmed = url.trim()
        
        // Must start with http:// or https://
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            return false
        }
        
        // Must not end with trailing slash
        if (trimmed.endsWith("/")) {
            return false
        }
        
        // Basic format check (host:port or just host)
        val urlPattern = Regex("^https?://[a-zA-Z0-9.-]+(:[0-9]+)?$")
        return urlPattern.matches(trimmed)
    }
    
    /**
     * Get health check URL for backend.
     * 
     * @return URL for /health endpoint
     */
    fun getHealthUrl(): String {
        return "$backendUrl/health"
    }
    
    /**
     * Get sessions URL for backend.
     * 
     * @return URL for /sessions endpoint
     */
    fun getSessionsUrl(): String {
        return "$backendUrl/sessions"
    }
}
