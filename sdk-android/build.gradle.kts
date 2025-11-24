plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

import java.util.Locale

android {
    namespace = "rayskillkit.core"
    compileSdk = 34

    defaultConfig {
        minSdk = 24
        targetSdk = 34
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("boolean", "USE_ANDROID_ORT", "false")
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
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    testImplementation(kotlin("test"))
    testImplementation("junit:junit:4.13.2")
    testImplementation("com.goterl:lazysodium-java:5.1.0")
    testImplementation("net.java.dev.jna:jna:5.13.0")
    testImplementation("com.squareup.okhttp3:mockwebserver:4.12.0")
}
