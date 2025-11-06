package rayskillkit

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import rayskillkit.core.FeaturePayload
import rayskillkit.core.SkillFeatureBuilder

class FeatureBuilderShapeTest {
    private val payload: FeaturePayload = mapOf(
        "correctCount" to 7f,
        "incorrectCount" to 3f,
        "gradeLevel" to 10f,
        "difficulty" to 6f,
        "question" to "Explain quantum computing in math and science contexts",
        "topic" to "math science coding",
        "timeRemaining" to 24f,
        "hints" to listOf("Use binary", "Review qubits"),
        "equation" to "2x + 3 = 7",
        "needsStepByStep" to true,
        "price" to 129.99f,
        "listPrice" to 199.99f,
        "discount" to 35f,
        "inventory" to 50f,
        "capacity" to 200f,
        "basketSize" to 3f,
        "description" to "Premium bundle sale for subscription retail insights",
        "intent" to "plan travel flight hotel sale",
        "productName" to "SmartGlass subscription",
        "pricingFormula" to "0.8 * list",
        "loyalCustomer" to true,
        "completedSteps" to 3f,
        "totalSteps" to 5f,
        "distanceKm" to 1200f,
        "durationHours" to 24f,
        "budgetUsd" to 5000f,
        "layovers" to listOf("LAX", "NRT"),
        "notes" to "Flight and hotel booking with emergency support",
        "destination" to "东京",
        "international" to true,
        "routingFormula" to "distance / speed",
        "heartRate" to 88f,
        "temperatureC" to 37.5f,
        "oxygenSaturation" to 98f,
        "severity" to 2f,
        "symptoms" to "cough fever pain",
        "diagnosis" to "infection",
        "isEmergency" to false,
        "medicationAdherence" to 80f,
        "allergies" to listOf("peanut"),
        "dosageFormula" to "weight * 0.1",
        "amount" to 45000f,
        "termMonths" to 36f,
        "interestRate" to 5.5f,
        "riskScore" to 60f,
        "approvedAmount" to 30000f,
        "requestedAmount" to 40000f,
        "requiresManualReview" to true,
        "useCase" to "investment loan",
        "documents" to listOf("ID", "Report"),
        "amortizationFormula" to "principal * rate",
        "occupiedRooms" to 80f,
        "totalRooms" to 100f,
        "stayLength" to 5f,
        "guestRating" to 4.5f,
        "amenities" to listOf("spa", "event"),
        "preferences" to "business conference spa",
        "purpose" to "conference",
        "vipGuest" to false,
        "cleanRooms" to 90f,
        "roomType" to "Executive suite",
        "pricingModel" to "base + premium",
        "weightKg" to 400f,
        "priority" to 7f,
        "deliveredStops" to 3f,
        "totalStops" to 5f,
        "stops" to listOf("A", "B", "C"),
        "status" to "loaded and customs cleared",
        "hazardous" to false,
        "routeId" to "R-2048",
        "throughput" to 6000f,
        "downtimeMinutes" to 120f,
        "defectRate" to 5f,
        "completedUnits" to 4500f,
        "plannedUnits" to 5000f,
        "lineStatus" to "maintenance alert quality",
        "alerts" to listOf("quality", "materials"),
        "maintenanceRequired" to true,
        "soilMoisture" to 55f,
        "rainfallMm" to 20f,
        "growthStage" to 4f,
        "healthyPlants" to 900f,
        "totalPlants" to 1000f,
        "crop" to "水稻",
        "cropStatus" to "yield pest",
        "issues" to "drought pest",
        "irrigationNeeded" to true,
        "soilPh" to 6.5f,
        "consumptionMw" to 12000f,
        "productionMw" to 15000f,
        "renewableShare" to 0.45f,
        "batteryLevel" to 60f,
        "batteryCapacity" to 100f,
        "outages" to listOf("grid", "maintenance"),
        "gridStatus" to "peak maintenance",
        "peakDemand" to true,
        "region" to "华东",
        "loadForecastFormula" to "sin(t)",
        "alertLevel" to 8f,
        "sensorsTriggered" to 12f,
        "resolvedIncidents" to 4f,
        "openIncidents" to 5f,
        "location" to "总部入口",
        "summary" to "intrusion door tamper",
        "verified" to true,
        "cameras" to listOf("Cam1", "Cam2"),
        "thresholdFormula" to "0.7 * base",
        "durationMinutes" to 140f,
        "rating" to 8.5f,
        "title" to "全球音乐会",
        "genre" to "live action drama",
        "mood" to "excited",
        "query" to "kids live sports",
        "ticketsSold" to 5000f,
        "capacity" to 5500f,
        "isLive" to true,
        "audienceAge" to 25f,
        "scheduleFormula" to "start + interval"
    )

    @Test
    fun buildersRespectRequestedInputDimensions() {
        listOf(8, 32, 64).forEach { inputDim ->
            SkillFeatureBuilder.all.forEach { builder ->
                val features = builder.build(payload, inputDim)
                assertEquals(
                    inputDim,
                    features.size,
                    "Builder ${builder.trigger} should return vector of size $inputDim"
                )
            }
        }
    }

    @Test
    fun buildersProduceMeaningfulSignals() {
        SkillFeatureBuilder.all.forEach { builder ->
            val features = builder.build(payload, 64)
            assertTrue(
                features.any { it != 0f },
                "Expected non-zero features from builder ${builder.trigger}"
            )
        }
    }
}

