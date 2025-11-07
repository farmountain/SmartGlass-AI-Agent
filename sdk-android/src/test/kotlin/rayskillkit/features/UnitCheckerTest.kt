package rayskillkit.features

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class UnitCheckerTest {
    @Test
    fun `parse simple dimension`() {
        val dimension = UnitChecker.parseDimension("kg*m/s^2")
        assertEquals(1, dimension.exponentOf("kg"))
        assertEquals(1, dimension.exponentOf("m"))
        assertEquals(-2, dimension.exponentOf("s"))
        assertFalse(dimension.isDimensionless())
        assertEquals("kg*m*s^-2", dimension.toString())
    }

    @Test
    fun `dimensionless inputs`() {
        assertTrue(UnitChecker.parseDimension(null).isDimensionless())
        assertTrue(UnitChecker.parseDimension("").isDimensionless())
        assertTrue(UnitChecker.parseDimension("1").isDimensionless())
    }

    @Test
    fun `compatibility check`() {
        val acceleration = UnitChecker.parseDimension("m/s^2")
        val expected = UnitChecker.parseDimension("m*s^-2")
        assertTrue(UnitChecker.areCompatible(acceleration, expected))
        assertTrue(UnitChecker.areCompatible("m/s^2", "m*s^-2"))
        val velocity = UnitChecker.parseDimension("m/s")
        assertFalse(UnitChecker.areCompatible(acceleration, velocity))
    }

    @Test
    fun `multiplication and division`() {
        val length = UnitChecker.parseDimension("m")
        val time = UnitChecker.parseDimension("s")
        val velocity = UnitChecker.divide(length, time)
        val area = UnitChecker.multiply(length, length)
        assertEquals("m*s^-1", velocity.toString())
        assertEquals("m^2", area.toString())
    }

    @Test
    fun `require compatible throws`() {
        val length = UnitChecker.parseDimension("m")
        val time = UnitChecker.parseDimension("s")
        assertFailsWith<IllegalArgumentException> {
            UnitChecker.requireCompatible(length, time)
        }
    }

    @Test
    fun `invalid tokens`() {
        assertFailsWith<IllegalArgumentException> {
            UnitChecker.parseDimension("^2")
        }
        assertFailsWith<IllegalArgumentException> {
            UnitChecker.parseDimension("m^two")
        }
    }
}
