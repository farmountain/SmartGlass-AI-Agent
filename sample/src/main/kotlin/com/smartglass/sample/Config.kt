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
     * Uses Android's URLUtil for comprehensive validation, with additional
     * checks for trailing slashes which cause API routing issues.
     * 
     * @param url URL to validate
     * @return Pair of (isValid, errorMessage). errorMessage is null if valid.
     */
    fun validateBackendUrl(url: String): Pair<Boolean, String?> {
        val trimmed = url.trim()
        
        // Must not be empty
        if (trimmed.isEmpty()) {
            return Pair(false, "URL cannot be empty")
        }
        
        // Must start with http:// or https://
        if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
            return Pair(false, "URL must start with http:// or https://")
        }
        
        // Must not end with trailing slash (causes routing issues)
        if (trimmed.endsWith("/")) {
            return Pair(false, "URL should not end with /")
        }
        
        // Use Android URLUtil for comprehensive validation
        try {
            android.webkit.URLUtil.isValidUrl(trimmed)
            return Pair(true, null)
        } catch (e: Exception) {
            return Pair(false, "Invalid URL format")
        }
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
