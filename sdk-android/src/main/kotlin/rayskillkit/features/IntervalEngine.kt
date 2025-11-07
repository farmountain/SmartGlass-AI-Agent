package rayskillkit.features

import kotlin.math.abs
import kotlin.math.max

/**
 * Numerical helpers for operating on value intervals and propagating Gaussian errors.
 */
object IntervalEngine {
    data class Interval(val lower: Double, val upper: Double) {
        init {
            require(!lower.isNaN() && !lower.isInfinite() && !upper.isNaN() && !upper.isInfinite()) {
                "Interval bounds must be finite numbers"
            }
            require(lower <= upper) { "Inverted interval [$lower, $upper]" }
        }

        val width: Double get() = upper - lower
        val center: Double get() = (lower + upper) / 2.0

        companion object {
            fun point(value: Double): Interval = Interval(value, value)
        }
    }

    data class ErrorEstimate(val mean: Double, val std: Double, val interval: Interval)

    fun plus(first: Interval, second: Interval): Interval =
        Interval(first.lower + second.lower, first.upper + second.upper)

    fun minus(first: Interval, second: Interval): Interval =
        Interval(first.lower - second.upper, first.upper - second.lower)

    fun times(first: Interval, second: Interval): Interval {
        val products = listOf(
            first.lower * second.lower,
            first.lower * second.upper,
            first.upper * second.lower,
            first.upper * second.upper,
        )
        val minValue = products.minOrNull() ?: 0.0
        val maxValue = products.maxOrNull() ?: 0.0
        return Interval(minValue, maxValue)
    }

    fun propagateError(mean: Double, std: Double, op: (Double) -> Double): ErrorEstimate {
        require(std >= 0) { "Standard deviation must be non-negative" }
        val propagatedMean = op(mean)
        if (std == 0.0) {
            val interval = Interval.point(propagatedMean)
            return ErrorEstimate(propagatedMean, 0.0, interval)
        }

        val epsilon = max(1e-6, abs(mean) * 1e-6)
        val forward = op(mean + epsilon)
        val backward = op(mean - epsilon)
        val derivative = (forward - backward) / (2 * epsilon)
        val propagatedStd = abs(derivative) * std
        val intervalRadius = 3.0 * propagatedStd
        val interval = Interval(propagatedMean - intervalRadius, propagatedMean + intervalRadius)
        return ErrorEstimate(propagatedMean, propagatedStd, interval)
    }
}
