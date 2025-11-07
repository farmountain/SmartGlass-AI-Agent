package rayskillkit.features

/**
 * Utility helpers for parsing and validating dimensional unit specifications.
 */
object UnitChecker {

    /**
     * A normalized representation of a dimensionality definition. Each entry maps a unit symbol to
     * its exponent. Zero exponents are omitted in order to guarantee canonical equality semantics.
     */
    data class Dimension internal constructor(private val exponents: Map<String, Int>) {
        val components: Map<String, Int> = exponents.toSortedMap()

        fun exponentOf(symbol: String): Int = components[symbol] ?: 0

        fun isDimensionless(): Boolean = components.isEmpty()

        override fun toString(): String {
            if (components.isEmpty()) return "1"
            return components.entries.joinToString(separator = "*") { (unit, power) ->
                when (power) {
                    1 -> unit
                    else -> "$unit^$power"
                }
            }
        }
    }

    /** Parses [spec] into a [Dimension]. */
    fun parseDimension(spec: String?): Dimension {
        if (spec == null) return Dimension(emptyMap())
        val trimmed = spec.trim()
        if (trimmed.isEmpty() || trimmed == "1") {
            return Dimension(emptyMap())
        }

        val tokens = tokenize(trimmed)
        val accumulator = mutableMapOf<String, Int>()
        var invertNext = false
        var expectOperand = true

        tokens.forEach { token ->
            when (token) {
                "*", "/" -> {
                    require(!expectOperand) { "Unexpected operator '$token' in '$spec'" }
                    invertNext = token == "/"
                    expectOperand = true
                }

                else -> {
                    require(expectOperand) { "Unexpected unit '$token' in '$spec'" }
                    val (unit, power) = parseUnit(token)
                    val signedPower = if (invertNext) -power else power
                    accumulator[unit] = (accumulator[unit] ?: 0) + signedPower
                    invertNext = false
                    expectOperand = false
                }
            }
        }

        require(!expectOperand) { "Dangling operator in '$spec'" }

        val normalized = accumulator.filterValues { it != 0 }
        return Dimension(normalized)
    }

    fun areCompatible(first: String?, second: String?): Boolean =
        areCompatible(parseDimension(first), parseDimension(second))

    fun areCompatible(first: Dimension, second: Dimension): Boolean =
        first.components == second.components

    fun multiply(vararg dimensions: Dimension): Dimension {
        val accumulator = mutableMapOf<String, Int>()
        dimensions.forEach { dimension ->
            dimension.components.forEach { (unit, power) ->
                accumulator[unit] = (accumulator[unit] ?: 0) + power
            }
        }
        return Dimension(accumulator.filterValues { it != 0 })
    }

    fun divide(numerator: Dimension, denominator: Dimension): Dimension {
        val accumulator = numerator.components.toMutableMap()
        denominator.components.forEach { (unit, power) ->
            accumulator[unit] = (accumulator[unit] ?: 0) - power
        }
        return Dimension(accumulator.filterValues { it != 0 })
    }

    fun requireCompatible(expected: Dimension, actual: Dimension, message: String? = null) {
        if (!areCompatible(expected, actual)) {
            val base = "Expected $expected but received $actual"
            throw IllegalArgumentException(message?.let { "$base: $it" } ?: base)
        }
    }

    fun requireCompatible(expected: String?, actual: String?, message: String? = null) {
        requireCompatible(parseDimension(expected), parseDimension(actual), message)
    }

    private fun tokenize(spec: String): List<String> {
        val sanitized = spec.replace("*", " * ").replace("/", " / ")
        return sanitized.split(Regex("\\s+")).filter { it.isNotEmpty() }
    }

    private fun parseUnit(token: String): Pair<String, Int> {
        val parts = token.split("^", limit = 2)
        val unit = parts[0].trim()
        require(unit.isNotEmpty()) { "Invalid unit token: '$token'" }
        val exponent = if (parts.size == 2) {
            parts[1].trim().toIntOrNull()
                ?: throw IllegalArgumentException("Invalid exponent in '$token'")
        } else {
            1
        }
        return unit to exponent
    }
}
