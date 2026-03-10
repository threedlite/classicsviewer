# Google Play Age Signals API - Android Implementation Guide

This document describes how to implement age verification using Google's Play Age Signals API in an Android app, based on the implementation in ClassicsViewer.

## Overview

The Play Age Signals API allows apps to check the age of users via Google Play account data. It works only for apps installed from the Google Play Store. For sideloaded or debug builds, the API gracefully falls back to allowing access.

**Key behavior**: The API is server-side — the app never collects or stores age data. Google Play returns a verification status and optional age range based on the user's Play account.

## 1. Add the Dependency

In `app/build.gradle`:

```gradle
dependencies {
    implementation 'com.google.android.play:age-signals:0.0.3'
}
```

## 2. Create the Layout

`res/layout/activity_age_verification.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:padding="32dp">

    <TextView
        android:id="@+id/verificationTitle"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Age Verification"
        android:textSize="24sp"
        android:textStyle="bold"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintBottom_toTopOf="@+id/verificationMessage"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintVertical_chainStyle="packed" />

    <TextView
        android:id="@+id/verificationMessage"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:text="Verifying age requirements..."
        android:textSize="16sp"
        android:gravity="center"
        android:layout_marginTop="16dp"
        app:layout_constraintTop_toBottomOf="@+id/verificationTitle"
        app:layout_constraintBottom_toTopOf="@+id/verificationProgress"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <ProgressBar
        android:id="@+id/verificationProgress"
        style="@style/Widget.AppCompat.ProgressBar"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:layout_marginTop="32dp"
        app:layout_constraintTop_toBottomOf="@+id/verificationMessage"
        app:layout_constraintBottom_toTopOf="@+id/retryButton"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <Button
        android:id="@+id/retryButton"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Retry"
        android:visibility="gone"
        android:layout_marginTop="16dp"
        app:layout_constraintTop_toBottomOf="@+id/verificationProgress"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

## 3. Create the Activity

`AgeVerificationActivity.kt`:

```kotlin
package com.example.yourapp

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.yourapp.databinding.ActivityAgeVerificationBinding
import com.google.android.play.agesignals.AgeSignalsException
import com.google.android.play.agesignals.AgeSignalsManager
import com.google.android.play.agesignals.AgeSignalsManagerFactory
import com.google.android.play.agesignals.AgeSignalsRequest
import com.google.android.play.agesignals.AgeSignalsResult
import com.google.android.play.agesignals.model.AgeSignalsErrorCode
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class AgeVerificationActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAgeVerificationBinding
    private lateinit var ageSignalsManager: AgeSignalsManager
    private var retryAttempts = 0
    private val maxRetryAttempts = 3

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAgeVerificationBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Initialize Age Signals Manager
        try {
            ageSignalsManager = AgeSignalsManagerFactory.create(applicationContext)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create AgeSignalsManager", e)
            handleVerificationError("Age verification service is not available", isRetryable = true)
            return
        }

        binding.retryButton.setOnClickListener {
            retryAttempts = 0
            checkAgeSignals()
        }

        checkAgeSignals()
    }

    private fun checkAgeSignals() {
        binding.verificationProgress.visibility = View.VISIBLE
        binding.retryButton.visibility = View.GONE
        binding.verificationMessage.text = "Verifying age requirements..."

        val request = AgeSignalsRequest.builder().build()

        ageSignalsManager.checkAgeSignals(request)
            .addOnSuccessListener { result ->
                handleAgeSignalsResult(result)
            }
            .addOnFailureListener { exception ->
                Log.e(TAG, "Age signals check failed", exception)
                val errorCode = (exception as? AgeSignalsException)?.errorCode

                when (errorCode) {
                    // Network error - block access until connected
                    AgeSignalsErrorCode.NETWORK_ERROR -> {
                        handleNetworkError()
                    }
                    // Not installed from Play Store (debug/sideloaded) - allow access
                    AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE,
                    AgeSignalsErrorCode.APP_NOT_OWNED -> {
                        Log.w(TAG, "Not a Play Store install - allowing access")
                        proceedToApp()
                    }
                    // API not available in region - allow access
                    AgeSignalsErrorCode.API_NOT_AVAILABLE -> {
                        Log.w(TAG, "API not available in region - allowing access")
                        proceedToApp()
                    }
                    // Play Store/Services issues - allow access
                    AgeSignalsErrorCode.PLAY_STORE_NOT_FOUND,
                    AgeSignalsErrorCode.PLAY_SERVICES_NOT_FOUND,
                    AgeSignalsErrorCode.PLAY_STORE_VERSION_OUTDATED,
                    AgeSignalsErrorCode.PLAY_SERVICES_VERSION_OUTDATED -> {
                        Log.w(TAG, "Play Store/Services issue - allowing access")
                        proceedToApp()
                    }
                    // Transient errors - retry
                    AgeSignalsErrorCode.CLIENT_TRANSIENT_ERROR -> {
                        handleVerificationError(
                            "Verification failed: ${exception.message}",
                            isRetryable = true
                        )
                    }
                    else -> {
                        handleVerificationError(
                            "Verification failed: ${exception.message}",
                            isRetryable = true
                        )
                    }
                }
            }
    }

    @Suppress("CAST_NEVER_SUCCEEDS")
    private fun handleAgeSignalsResult(result: AgeSignalsResult) {
        // userStatus() returns an @IntDef annotated value
        val statusValue = result.userStatus() as? Int ?: -1
        val ageLower: Int? = result.ageLower()
        val ageUpper: Int? = result.ageUpper()

        Log.d(TAG, "Result - status: $statusValue, ageLower: $ageLower, ageUpper: $ageUpper")

        // Status values:
        //   VERIFIED=0        - User verified as adult
        //   SUPERVISED=1      - Supervised account
        //   SUPERVISED_APPROVAL_PENDING=2
        //   SUPERVISED_APPROVAL_DENIED=3
        //   UNKNOWN=4
        val isEligible = when {
            statusValue == 0 -> true  // VERIFIED = adult
            ageLower != null && ageLower >= 18 -> true  // Age range confirms 18+
            ageLower == null && ageUpper == null -> true // No data = unsupported region
            else -> false
        }

        if (isEligible) {
            proceedToApp()
        } else {
            showAgeRestrictionMessage()
        }
    }

    private fun handleNetworkError() {
        binding.verificationProgress.visibility = View.GONE

        if (retryAttempts < maxRetryAttempts) {
            retryAttempts++
            binding.verificationMessage.text =
                "No internet connection.\n\nAge verification requires internet.\n\nRetrying... ($retryAttempts/$maxRetryAttempts)"
            lifecycleScope.launch {
                delay(3000)
                checkAgeSignals()
            }
        } else {
            binding.verificationMessage.text =
                "No internet connection.\n\nPlease connect and tap Retry."
            binding.retryButton.visibility = View.VISIBLE
        }
    }

    private fun handleVerificationError(errorMessage: String, isRetryable: Boolean) {
        binding.verificationProgress.visibility = View.GONE

        if (isRetryable && retryAttempts < maxRetryAttempts) {
            retryAttempts++
            binding.verificationMessage.text = "$errorMessage\n\nRetrying... ($retryAttempts/$maxRetryAttempts)"
            lifecycleScope.launch {
                delay(2000)
                checkAgeSignals()
            }
        } else {
            binding.verificationMessage.text = "$errorMessage\n\nPlease check your connection and try again."
            binding.retryButton.visibility = View.VISIBLE
        }
    }

    private fun showAgeRestrictionMessage() {
        binding.verificationProgress.visibility = View.GONE
        binding.verificationMessage.text =
            "This app is restricted to users 18 years of age and older."
        Toast.makeText(this, "Age restriction: You must be 18 or older", Toast.LENGTH_LONG).show()

        lifecycleScope.launch {
            delay(3000)
            finishAffinity() // Close app
        }
    }

    private fun proceedToApp() {
        // Replace YourMainActivity with your actual main activity
        startActivity(Intent(this, YourMainActivity::class.java))
        finish()
    }

    override fun onBackPressed() {
        // Block back button during verification
    }

    companion object {
        private const val TAG = "AgeVerification"
    }
}
```

## 4. Configure the Manifest

Make `AgeVerificationActivity` the launcher activity (entry point), so age verification runs before the user can access the app:

```xml
<activity
    android:name=".AgeVerificationActivity"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>

<!-- Remove LAUNCHER intent-filter from your previous main activity -->
<activity android:name=".YourMainActivity" />
```

## 5. Error Handling Strategy

The API can fail for many reasons. The implementation uses this policy:

| Error Code | Action | Rationale |
|---|---|---|
| `CANNOT_BIND_TO_SERVICE` | Allow access | Debug build or sideloaded APK |
| `APP_NOT_OWNED` | Allow access | Not installed from Play Store |
| `API_NOT_AVAILABLE` | Allow access | Unsupported region |
| `PLAY_STORE_NOT_FOUND` | Allow access | No Play Store on device |
| `PLAY_SERVICES_NOT_FOUND` | Allow access | No Play Services |
| `PLAY_STORE_VERSION_OUTDATED` | Allow access | Old Play Store version |
| `PLAY_SERVICES_VERSION_OUTDATED` | Allow access | Old Play Services |
| `NETWORK_ERROR` | Block + auto-retry | Age data not cached, needs internet |
| `CLIENT_TRANSIENT_ERROR` | Auto-retry (up to 3x) | Temporary failure |

This ensures the app is not unusable on devices without Play Store while still enforcing age verification when the API is available.

## 6. Result Interpretation

`AgeSignalsResult` provides:

- **`userStatus()`**: Int status code
  - `0` (VERIFIED) — User is a verified adult
  - `1` (SUPERVISED) — Supervised account (e.g., Family Link)
  - `2` (SUPERVISED_APPROVAL_PENDING)
  - `3` (SUPERVISED_APPROVAL_DENIED)
  - `4` (UNKNOWN)
- **`ageLower()`**: Lower bound of age range (nullable)
- **`ageUpper()`**: Upper bound of age range (nullable)

Decision logic:
1. `VERIFIED` status → allow (user is an adult)
2. `ageLower >= 18` → allow (age range confirms 18+)
3. Both `ageLower` and `ageUpper` are null → allow (unsupported region, no data available)
4. Otherwise → deny access

## 7. Important Notes

- **No permissions required**: The API works through Play Services, no manifest permissions needed.
- **Play Store only**: The API only returns meaningful results for apps installed from Google Play. Debug/sideloaded builds will get `CANNOT_BIND_TO_SERVICE` or `APP_NOT_OWNED`.
- **Regional availability**: The API is not available in all regions. When unavailable, `API_NOT_AVAILABLE` is returned.
- **No user data stored**: The app never sees or stores the user's actual age — only a verification status and optional age range from Google.
- **Minimum age is configurable**: Change `>= 18` to your required age threshold.
