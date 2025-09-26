# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# Uncomment this to preserve the line number information for
# debugging stack traces.
-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile

# Keep model classes for Gson serialization
-keep class com.classicsviewer.app.models.** { *; }
-keepclassmembers class com.classicsviewer.app.models.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
-keepattributes EnclosingMethod
-keepattributes InnerClasses

# Gson specific rules
-keep class com.google.gson.** { *; }
-keep class com.google.gson.stream.** { *; }
-keep class com.google.gson.reflect.TypeToken { *; }
-keep class * extends com.google.gson.reflect.TypeToken

# Keep TypeToken and its generic signatures
-keep class com.google.gson.reflect.TypeToken {
    private final java.lang.Class rawType;
    private final java.lang.reflect.Type type;
    private final int hashCode;
}
-keep class com.google.gson.internal.bind.TypeAdapters { *; }
-keep class com.google.gson.internal.bind.TypeAdapters$* { *; }
-keep class com.google.gson.internal.Excluder { *; }
-keep class com.google.gson.internal.** { *; }

# Keep all classes that are serialized/deserialized by Gson
-keep class * implements com.google.gson.TypeAdapter
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer

# Prevent obfuscation of classes with @SerializedName annotation
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

# Missing classes from XML parsing libraries
-dontwarn aQute.bnd.annotation.spi.ServiceProvider
-dontwarn com.google.android.gms.common.annotation.NoNullnessRewrite
-dontwarn javax.xml.stream.XMLEventFactory
-dontwarn javax.xml.stream.XMLInputFactory
-dontwarn javax.xml.stream.XMLOutputFactory
-dontwarn javax.xml.stream.XMLResolver
-dontwarn javax.xml.stream.util.XMLEventAllocator