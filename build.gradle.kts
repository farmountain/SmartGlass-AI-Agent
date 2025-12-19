plugins {
    id("com.android.application") version "8.2.2" apply false
    id("com.android.library") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.22" apply false
}

allprojects {
    repositories {
        google()
        mavenCentral()
        
        // Meta Wearables Device Access Toolkit (DAT) SDK uses Application ID only
        // Following Meta's official documentation: only Application ID required
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.buildDir)
}
