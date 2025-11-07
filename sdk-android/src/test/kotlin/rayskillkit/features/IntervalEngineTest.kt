package rayskillkit.features

import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class IntervalEngineTest {
    @Test
    fun `interval addition`() {
        val a = IntervalEngine.Interval(1.0, 2.0)
        val b = IntervalEngine.Interval(-1.0, 3.0)
        val sum = IntervalEngine.plus(a, b)
        assertEquals(0.0, sum.lower)
        assertEquals(5.0, sum.upper)
    }

    @Test
    fun `interval subtraction`() {
        val a = IntervalEngine.Interval(4.0, 5.0)
        val b = IntervalEngine.Interval(1.0, 2.0)
        val diff = IntervalEngine.minus(a, b)
        assertEquals(2.0, diff.lower)
        assertEquals(4.0, diff.upper)
    }

    @Test
    fun `interval multiplication`() {
        val a = IntervalEngine.Interval(-2.0, 3.0)
        val b = IntervalEngine.Interval(0.5, 2.0)
        val product = IntervalEngine.times(a, b)
        assertEquals(-4.0, product.lower)
        assertEquals(6.0, product.upper)
    }

    @Test
    fun `zero width interval`() {
        val point = IntervalEngine.Interval.point(3.5)
        val sum = IntervalEngine.plus(point, IntervalEngine.Interval(1.0, 1.0))
        assertEquals(4.5, sum.lower)
        assertEquals(sum.lower, sum.upper)
    }

    @Test
    fun `inverted intervals are rejected`() {
        assertFailsWith<IllegalArgumentException> {
            IntervalEngine.Interval(3.0, 2.0)
        }
    }

    @Test
    fun `error propagation linear`() {
        val estimate = IntervalEngine.propagateError(5.0, 0.5) { value -> 2.0 * value + 1.0 }
        assertEquals(11.0, estimate.mean, absoluteTolerance)
        assertEquals(1.0, estimate.std, absoluteTolerance)
        assertEquals(estimate.mean - 3 * estimate.std, estimate.interval.lower, absoluteTolerance)
        assertEquals(estimate.mean + 3 * estimate.std, estimate.interval.upper, absoluteTolerance)
    }

    @Test
    fun `error propagation nonlinear`() {
        val estimate = IntervalEngine.propagateError(2.0, 0.1) { value -> value * value }
        assertEquals(4.0, estimate.mean, absoluteTolerance)
        assertTrue(estimate.std > 0)
        val expectedStd = abs(2 * 2.0) * 0.1
        assertEquals(expectedStd, estimate.std, 1e-3)
    }

    @Test
    fun `negative standard deviation`() {
        assertFailsWith<IllegalArgumentException> {
            IntervalEngine.propagateError(0.0, -1.0) { it }
        }
    }

    companion object {
        private const val absoluteTolerance = 1e-6
    }
}
