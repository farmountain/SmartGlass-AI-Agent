package com.smartglass.sdk.rayban

import android.content.Context
import android.util.Log

/**
 * Meta Wearables Device Access Toolkit (DAT) SDK initializer and helper.
 * 
 * This class handles the proper initialization of the Meta DAT SDK and provides
 * helper methods for common DAT SDK operations following the official Meta documentation.
 */
object MetaDatSdkInitializer {
    
    private const val TAG = "MetaDatSDK"
    private var initialized = false
    
    /**
     * Initialize the Meta DAT SDK. This must be called once per process at startup.
     * 
     * Based on Meta documentation:
     * "Initialize the SDK once per process at start up. Invoking other Wearables Device 
     * Access Toolkit APIs before initialization yields WearablesError.NOT_INITIALIZED."
     * 
     * @param context Application context
     * @return true if initialization successful, false if DAT SDK not available
     */
    fun initialize(context: Context): Boolean {
        if (initialized) {
            Log.d(TAG, "Meta DAT SDK already initialized")
            return true
        }
        
        return runCatching {
            // Try to load and initialize the Meta Wearables class
            val wearablesClass = Class.forName("com.meta.wearable.dat.core.Wearables")
            val initializeMethod = wearablesClass.getDeclaredMethod("initialize", Context::class.java)
            
            initializeMethod.invoke(null, context.applicationContext)
            initialized = true
            
            Log.i(TAG, "✅ Meta DAT SDK initialized successfully")
            true
            
        }.getOrElse { exception ->
            Log.w(TAG, "❌ Meta DAT SDK not available - using mock fallback", exception)
            false
        }
    }
    
    /**
     * Check if the Meta DAT SDK is properly initialized and available.
     */
    fun isInitialized(): Boolean = initialized
    
    /**
     * Get the Wearables class if available.
     */
    fun getWearablesClass(): Class<*>? {
        return if (initialized) {
            try {
                Class.forName("com.meta.wearable.dat.core.Wearables")
            } catch (e: ClassNotFoundException) {
                null
            }
        } else {
            null
        }
    }
    
    /**
     * Helper to check if Meta DAT SDK classes are available in the classpath.
     */
    fun isDatSdkAvailable(): Boolean {
        return runCatching {
            // Check for core DAT SDK classes
            Class.forName("com.meta.wearable.dat.core.Wearables")
            Class.forName("com.meta.wearable.dat.camera.StreamSession")
            Class.forName("com.meta.wearable.dat.core.types.Permission")
            true
        }.getOrElse { false }
    }
    
    /**
     * Get Meta DAT SDK version information if available.
     */
    fun getSdkVersion(): String {
        return runCatching {
            val wearablesClass = getWearablesClass()
            // Try to get version info from the SDK
            // Note: This might need adjustment based on actual DAT SDK API
            "Meta DAT SDK (version detection not implemented)"
        }.getOrElse { "DAT SDK not available" }
    }
    
    /**
     * Log current Meta DAT SDK status for debugging.
     */
    fun logSdkStatus() {
        Log.i(TAG, "=== Meta DAT SDK Status ===")
        Log.i(TAG, "Initialized: $initialized")
        Log.i(TAG, "SDK Available: ${isDatSdkAvailable()}")
        Log.i(TAG, "Version: ${getSdkVersion()}")
        
        if (isDatSdkAvailable()) {
            Log.i(TAG, "✅ Ready for Meta Ray-Ban glasses integration")
        } else {
            Log.i(TAG, "ℹ️  Using mock implementation for development")
        }
    }
}