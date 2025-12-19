package com.smartglass.sdk.common

/**
 * Common error response structure used across SmartGlass API clients.
 */
data class ErrorResponse(
    val detail: String? = null,
    val error: String? = null,
)