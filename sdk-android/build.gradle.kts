plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

import java.util.Locale

val useAndroidOrt = (project.findProperty("USE_ANDROID_ORT") as? String)?.toBoolean() ?: false

android {
    namespace = "rayskillkit.core"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
        targetSdk = 34
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("boolean", "USE_ANDROID_ORT", useAndroidOrt.toString())
        val isCi = System.getenv("CI")?.lowercase(Locale.US) == "true"
        buildConfigField("boolean", "IS_CI", isCi.toString())
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }

    testOptions {
        unitTests {
            isReturnDefaultValues = true
            isIncludeAndroidResources = false
        }
    }
}

dependencies {
    implementation("org.json:json:20240303")
    implementation("com.google.mlkit:text-recognition:16.0.0")
    implementation("com.google.android.gms:play-services-tasks:18.2.0")
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("com.goterl:lazysodium-android:5.1.0@aar")
    implementation("com.goterl:lazysodium-java:5.1.0")
    implementation("net.java.dev.jna:jna:5.13.0@aar")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    implementation("com.squareup.moshi:moshi-adapters:1.15.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Always compile against ONNX Runtime so inference wrappers are available while
    // still allowing the dependency to be optional at runtime for lightweight builds.
    compileOnly("com.microsoft.onnxruntime:onnxruntime-android:1.18.0")

    if (useAndroidOrt) {
        implementation("com.microsoft.onnxruntime:onnxruntime-android:1.18.0")
    }

    testImplementation(kotlin("test"))
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("com.goterl:lazysodium-java:5.1.0")
    testImplementation("net.java.dev.jna:jna:5.13.0")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
    testImplementation("org.robolectric:robolectric:4.12.2")
    testImplementation("androidx.test:core:1.5.0")
}
