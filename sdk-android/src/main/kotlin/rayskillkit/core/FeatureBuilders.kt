package rayskillkit.core

import kotlin.math.abs
import kotlin.math.min
import kotlin.math.sign

typealias FeaturePayload = Map<String, Any?>
typealias FeatureBuilder = (FeaturePayload, Int) -> FloatArray

const val DEFAULT_FEATURE_INPUT_DIM = 64

sealed interface SkillFeatureBuilder {
    val trigger: String

    fun build(payload: FeaturePayload, inputDim: Int = DEFAULT_FEATURE_INPUT_DIM): FloatArray

    companion object {
        val all: List<SkillFeatureBuilder> = listOf(
            Education,
            Retail,
            Travel,
            Health,
            Finance,
            Hospitality,
            Logistics,
            Manufacturing,
            Agriculture,
            Energy,
            Security,
            Entertainment,
        )

        val registry: Map<String, SkillFeatureBuilder> = all.associateBy { it.trigger }
    }

    object Education : SkillFeatureBuilder {
        override val trigger: String = "education"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildEducationFeatures(payload, inputDim)
    }

    object Retail : SkillFeatureBuilder {
        override val trigger: String = "retail"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildRetailFeatures(payload, inputDim)
    }

    object Travel : SkillFeatureBuilder {
        override val trigger: String = "travel"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildTravelFeatures(payload, inputDim)
    }

    object Health : SkillFeatureBuilder {
        override val trigger: String = "health"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildHealthFeatures(payload, inputDim)
    }

    object Finance : SkillFeatureBuilder {
        override val trigger: String = "finance"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildFinanceFeatures(payload, inputDim)
    }

    object Hospitality : SkillFeatureBuilder {
        override val trigger: String = "hospitality"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildHospitalityFeatures(payload, inputDim)
    }

    object Logistics : SkillFeatureBuilder {
        override val trigger: String = "logistics"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildLogisticsFeatures(payload, inputDim)
    }

    object Manufacturing : SkillFeatureBuilder {
        override val trigger: String = "manufacturing"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildManufacturingFeatures(payload, inputDim)
    }

    object Agriculture : SkillFeatureBuilder {
        override val trigger: String = "agriculture"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildAgricultureFeatures(payload, inputDim)
    }

    object Energy : SkillFeatureBuilder {
        override val trigger: String = "energy"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildEnergyFeatures(payload, inputDim)
    }

    object Security : SkillFeatureBuilder {
        override val trigger: String = "security"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildSecurityFeatures(payload, inputDim)
    }

    object Entertainment : SkillFeatureBuilder {
        override val trigger: String = "entertainment"
        override fun build(payload: FeaturePayload, inputDim: Int): FloatArray =
            buildEntertainmentFeatures(payload, inputDim)
    }
}

fun builderForSkill(trigger: String): SkillFeatureBuilder? = SkillFeatureBuilder.registry[trigger]

fun linearFeats(equation: String?): List<Float> {
    if (equation.isNullOrBlank()) {
        return List(4) { 0f }
    }

    val numbers = NUMBER_REGEX
        .findAll(equation)
        .mapNotNull { it.value.toFloatOrNull() }
        .map { it.toFloat() }
        .toList()

    val coefficients = MutableList(4) { 0f }
    val limit = min(coefficients.size, numbers.size)
    for (index in 0 until limit) {
        coefficients[index] = normalize(numbers[index], 100f)
    }

    val magnitude = numbers.fold(0f) { acc, value -> acc + abs(value) }
    coefficients[3] = normalize(magnitude, 400f)

    return coefficients
}

fun keywordFeats(text: String?, keywords: List<String>): List<Float> {
    if (text.isNullOrBlank()) {
        return List(keywords.size) { 0f }
    }

    val source = text.lowercase()
    return keywords.map { keyword -> if (source.contains(keyword.lowercase())) 1f else 0f }
}

fun normalizedLength(text: String?, maxLength: Int): Float {
    if (text.isNullOrEmpty() || maxLength <= 0) {
        return 0f
    }
    val bounded = text.length.coerceAtMost(maxLength)
    return clean(bounded.toFloat() / maxLength.toFloat())
}

private fun buildEducationFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    val correct = payload.float("correctCount") ?: 0f
    val incorrect = payload.float("incorrectCount") ?: 0f
    val totalAttempts = correct + incorrect

    features += normalize(payload.float("gradeLevel"), 12f)
    features += normalize(payload.float("difficulty"), 10f)
    features += normalizedLength(payload.string("question"), 256)
    features += normalize(payload.float("timeRemaining"), 60f)
    features += ratio(correct, totalAttempts)
    features += ratio(incorrect, totalAttempts)
    features += normalizedCount(payload.collectionSize("hints"), 10f)
    features += keywordFeats(payload.text("topic", "question"), listOf("math", "science", "history", "language", "coding", "exam"))
    features += linearFeats(payload.string("equation"))
    features += boolFlag(payload["needsStepByStep"])

    return composeVector(inputDim, features)
}

private fun buildRetailFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    val price = payload.float("price")
    val listPrice = payload.float("listPrice")

    features += normalize(price, 2000f)
    features += normalize(payload.float("discount"), 100f)
    features += ratio(payload.float("inventory"), payload.float("capacity"))
    features += normalize(payload.float("basketSize"), 50f)
    features += normalizedLength(payload.string("description"), 512)
    features += keywordFeats(payload.text("intent", "productName", "description"), listOf("sale", "new", "bundle", "premium", "limited", "subscription"))
    features += normalize(delta(price, listPrice), 500f)
    features += boolFlag(payload["loyalCustomer"])
    features += linearFeats(payload.string("pricingFormula"))

    return composeVector(inputDim, features)
}

private fun buildTravelFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    val progress = payload.float("completedSteps")
    val totalSteps = payload.float("totalSteps")

    features += normalize(payload.float("distanceKm"), 20000f)
    features += normalize(payload.float("durationHours"), 240f)
    features += normalize(payload.float("budgetUsd"), 20000f)
    features += ratio(progress, totalSteps)
    features += normalizedCount(payload.collectionSize("layovers"), 6f)
    features += keywordFeats(payload.text("notes", "destination", "intent"), listOf("flight", "hotel", "car", "visa", "delay", "emergency"))
    features += boolFlag(payload["international"])
    features += normalizedLength(payload.string("destination"), 64)
    features += linearFeats(payload.string("routingFormula"))

    return composeVector(inputDim, features)
}

private fun buildHealthFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("heartRate"), 200f)
    features += normalize(payload.float("temperatureC"), 45f)
    features += normalize(payload.float("oxygenSaturation"), 100f)
    features += normalize(payload.float("severity"), 5f)
    features += normalizedLength(payload.string("symptoms"), 256)
    features += keywordFeats(payload.text("symptoms", "diagnosis"), listOf("pain", "fever", "cough", "injury", "allergy", "infection"))
    features += boolFlag(payload["isEmergency"])
    features += normalize(payload.float("medicationAdherence"), 100f)
    features += normalizedCount(payload.collectionSize("allergies"), 10f)
    features += linearFeats(payload.string("dosageFormula"))

    return composeVector(inputDim, features)
}

private fun buildFinanceFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("amount"), 100_000f)
    features += normalize(payload.float("termMonths"), 360f)
    features += normalize(payload.float("interestRate"), 30f)
    features += normalize(payload.float("riskScore"), 100f)
    features += ratio(payload.float("approvedAmount"), payload.float("requestedAmount"))
    features += boolFlag(payload["requiresManualReview"])
    features += keywordFeats(payload.text("intent", "useCase"), listOf("loan", "investment", "budget", "savings", "fraud", "insurance"))
    features += normalizedCount(payload.collectionSize("documents"), 20f)
    features += linearFeats(payload.string("amortizationFormula"))

    return composeVector(inputDim, features)
}

private fun buildHospitalityFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += ratio(payload.float("occupiedRooms"), payload.float("totalRooms"))
    features += normalize(payload.float("stayLength"), 30f)
    features += normalize(payload.float("guestRating"), 5f)
    features += normalizedCount(payload.collectionSize("amenities"), 25f)
    features += keywordFeats(payload.text("preferences", "purpose"), listOf("business", "leisure", "family", "spa", "event", "conference"))
    features += boolFlag(payload["vipGuest"])
    features += ratio(payload.float("cleanRooms"), payload.float("totalRooms"))
    features += normalizedLength(payload.string("roomType"), 64)
    features += linearFeats(payload.string("pricingModel"))

    return composeVector(inputDim, features)
}

private fun buildLogisticsFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("weightKg"), 1000f)
    features += normalize(payload.float("distanceKm"), 10000f)
    features += normalize(payload.float("priority"), 10f)
    features += ratio(payload.float("deliveredStops"), payload.float("totalStops"))
    features += normalizedCount(payload.collectionSize("stops"), 20f)
    features += keywordFeats(payload.text("status", "notes"), listOf("delayed", "loaded", "customs", "handoff", "failed", "signed"))
    features += boolFlag(payload["hazardous"])
    features += normalizedLength(payload.string("routeId"), 48)
    features += linearFeats(payload.string("routingFormula"))

    return composeVector(inputDim, features)
}

private fun buildManufacturingFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("throughput"), 10_000f)
    features += normalize(payload.float("downtimeMinutes"), 1_440f)
    features += normalize(payload.float("defectRate"), 100f)
    features += ratio(payload.float("completedUnits"), payload.float("plannedUnits"))
    features += normalizedLength(payload.string("lineStatus"), 128)
    features += keywordFeats(payload.text("lineStatus", "alerts"), listOf("blocked", "maintenance", "overheat", "quality", "materials", "idle"))
    features += boolFlag(payload["maintenanceRequired"])
    features += normalize(payload.float("temperatureC"), 200f)
    features += normalizedCount(payload.collectionSize("alerts"), 15f)

    return composeVector(inputDim, features)
}

private fun buildAgricultureFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("soilMoisture"), 100f)
    features += normalize(payload.float("rainfallMm"), 500f)
    features += normalize(payload.float("growthStage"), 10f)
    features += normalize(payload.float("temperatureC"), 50f)
    features += ratio(payload.float("healthyPlants"), payload.float("totalPlants"))
    features += normalizedLength(payload.string("crop"), 64)
    features += keywordFeats(payload.text("cropStatus", "issues"), listOf("pest", "drought", "disease", "harvest", "fertilizer", "yield"))
    features += boolFlag(payload["irrigationNeeded"])
    features += normalize(payload.float("soilPh"), 14f)

    return composeVector(inputDim, features)
}

private fun buildEnergyFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("consumptionMw"), 100_000f)
    features += normalize(payload.float("productionMw"), 100_000f)
    features += normalize(payload.float("renewableShare"), 1f)
    features += ratio(payload.float("batteryLevel"), payload.float("batteryCapacity"))
    features += normalizedCount(payload.collectionSize("outages"), 20f)
    features += keywordFeats(payload.text("gridStatus", "alerts"), listOf("peak", "shortage", "maintenance", "surplus", "derate", "fault"))
    features += boolFlag(payload["peakDemand"])
    features += normalizedLength(payload.string("region"), 48)
    features += linearFeats(payload.string("loadForecastFormula"))

    return composeVector(inputDim, features)
}

private fun buildSecurityFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("alertLevel"), 10f)
    features += normalize(payload.float("sensorsTriggered"), 50f)
    features += ratio(payload.float("resolvedIncidents"), payload.float("openIncidents"))
    features += normalizedLength(payload.string("location"), 128)
    features += keywordFeats(payload.text("summary", "alerts"), listOf("intrusion", "fire", "door", "window", "panic", "tamper"))
    features += boolFlag(payload["verified"])
    features += normalizedCount(payload.collectionSize("cameras"), 50f)
    features += linearFeats(payload.string("thresholdFormula"))

    return composeVector(inputDim, features)
}

private fun buildEntertainmentFeatures(payload: FeaturePayload, inputDim: Int): FloatArray {
    val features = mutableListOf<Float>()

    features += normalize(payload.float("durationMinutes"), 240f)
    features += normalize(payload.float("rating"), 10f)
    features += normalizedLength(payload.string("title"), 96)
    features += keywordFeats(payload.text("genre", "mood", "query"), listOf("action", "comedy", "drama", "live", "kids", "sports"))
    features += ratio(payload.float("ticketsSold"), payload.float("capacity"))
    features += boolFlag(payload["isLive"])
    features += normalize(payload.float("audienceAge"), 100f)
    features += normalizedLength(payload.string("query"), 256)
    features += linearFeats(payload.string("scheduleFormula"))

    return composeVector(inputDim, features)
}

private fun composeVector(inputDim: Int, values: List<Float>): FloatArray {
    require(inputDim > 0) { "inputDim must be positive" }
    val vector = FloatArray(inputDim)
    val limit = min(values.size, inputDim)
    for (index in 0 until limit) {
        vector[index] = clean(values[index])
    }
    return vector
}

private fun normalize(value: Float?, scale: Float): Float {
    if (value == null || scale == 0f) {
        return 0f
    }
    val scaled = value / scale
    val clamped = when {
        scaled.isNaN() -> 0f
        scaled.isInfinite() -> sign(scaled)
        scaled > 1f -> 1f
        scaled < -1f -> -1f
        else -> scaled
    }
    return clamped
}

private fun ratio(part: Float?, total: Float?): Float {
    val numerator = part ?: return 0f
    val denominator = total ?: return 0f
    if (denominator == 0f) {
        return 0f
    }
    return clean((numerator / denominator).coerceIn(-1f, 1f))
}

private fun delta(current: Float?, reference: Float?): Float {
    val currentValue = current ?: return 0f
    val referenceValue = reference ?: return 0f
    val divisor = if (referenceValue == 0f) 1f else abs(referenceValue)
    return clean((currentValue - referenceValue) / divisor)
}

private fun normalizedCount(count: Float?, max: Float): Float {
    if (count == null || max <= 0f) {
        return 0f
    }
    return clean((count / max).coerceIn(0f, 1f))
}

private fun boolFlag(value: Any?): Float = when (value) {
    is Boolean -> if (value) 1f else 0f
    is Number -> if (value.toFloat() != 0f) 1f else 0f
    is String -> if (value.equals("true", ignoreCase = true)) 1f else 0f
    else -> 0f
}

private fun FeaturePayload.string(key: String): String? = when (val value = this[key]) {
    is String -> value
    is Number -> value.toString()
    is Boolean -> value.toString()
    else -> null
}

private fun FeaturePayload.text(vararg keys: String): String? {
    val pieces = keys.mapNotNull { key -> string(key)?.takeIf { it.isNotBlank() } }
    if (pieces.isEmpty()) {
        return null
    }
    return pieces.joinToString(" ")
}

private fun FeaturePayload.float(key: String): Float? = toFloat(this[key])

private fun FeaturePayload.collectionSize(key: String): Float? = sizeOf(this[key])

private fun toFloat(value: Any?): Float? = when (value) {
    null -> null
    is Float -> value
    is Double -> value.toFloat()
    is Int -> value.toFloat()
    is Long -> value.toFloat()
    is Short -> value.toFloat()
    is Byte -> value.toFloat()
    is Boolean -> if (value) 1f else 0f
    is String -> value.toFloatOrNull()
    else -> null
}

private fun sizeOf(value: Any?): Float? = when (value) {
    null -> null
    is Collection<*> -> value.size.toFloat()
    is Map<*, *> -> value.size.toFloat()
    is Array<*> -> value.size.toFloat()
    is IntArray -> value.size.toFloat()
    is LongArray -> value.size.toFloat()
    is FloatArray -> value.size.toFloat()
    is DoubleArray -> value.size.toFloat()
    is ShortArray -> value.size.toFloat()
    is ByteArray -> value.size.toFloat()
    is BooleanArray -> value.size.toFloat()
    is CharArray -> value.size.toFloat()
    is String -> value.length.toFloat()
    else -> null
}

private fun clean(value: Float): Float = when {
    value.isNaN() -> 0f
    value.isInfinite() -> sign(value)
    else -> value
}

private val NUMBER_REGEX = Regex("[-+]?\\d*\\.?\\d+")
