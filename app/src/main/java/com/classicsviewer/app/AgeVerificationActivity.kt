package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.databinding.ActivityAgeVerificationBinding
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.gms.tasks.Task
import com.google.android.play.agesignals.AgeSignalsManager
import com.google.android.play.agesignals.AgeSignalsManagerFactory
import com.google.android.play.agesignals.AgeSignalsRequest
import com.google.android.play.agesignals.AgeSignalsResult
import com.google.android.play.agesignals.model.AgeSignalsVerificationStatus
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class AgeVerificationActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAgeVerificationBinding
    private lateinit var ageSignalsManager: AgeSignalsManager
    private var retryAttempts = 0
    private val maxRetryAttempts = 3

    // Network error means age data is not cached and cannot be retrieved
    // This should block access until user connects to internet
    private val NETWORK_ERROR = -3

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAgeVerificationBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Apply color inversion setting
        val inverted = PreferencesManager.getInvertColors(this)
        if (inverted) {
            binding.root.setBackgroundColor(0xFFFFFFFF.toInt())
            binding.verificationTitle.setTextColor(0xFF000000.toInt())
            binding.verificationMessage.setTextColor(0xFF000000.toInt())
        } else {
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.verificationTitle.setTextColor(0xFFFFFFFF.toInt())
            binding.verificationMessage.setTextColor(0xFFFFFFFF.toInt())
        }

        // Initialize Age Signals Manager
        try {
            ageSignalsManager = AgeSignalsManagerFactory.create(applicationContext)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to create AgeSignalsManager", e)
            // If API is not available, show error and allow retry
            handleVerificationError("Age verification service is not available", isRetryable = true)
            return
        }

        // Setup retry button
        binding.retryButton.setOnClickListener {
            retryAttempts = 0
            checkAgeSignals()
        }

        // Start age verification
        checkAgeSignals()
    }

    private fun checkAgeSignals() {
        // Show progress, hide retry button
        binding.verificationProgress.visibility = View.VISIBLE
        binding.retryButton.visibility = View.GONE
        binding.verificationMessage.text = "Verifying age requirements...\nThis app is only available for users 18 and older."

        Log.d(TAG, "Checking age signals (attempt ${retryAttempts + 1}/$maxRetryAttempts)")

        val request = AgeSignalsRequest.builder().build()

        ageSignalsManager.checkAgeSignals(request)
            .addOnSuccessListener { result ->
                handleAgeSignalsResult(result)
            }
            .addOnFailureListener { exception ->
                Log.e(TAG, "Age signals check failed", exception)

                val errorMessage = exception.message?.lowercase() ?: ""

                // Check for network errors - these must block access
                // Network error means age data needs to be fetched but can't reach servers
                if (errorMessage.contains("network") ||
                    errorMessage.contains("connection") ||
                    errorMessage.contains("no available network")) {
                    Log.e(TAG, "Network error during age verification - blocking access until connected")
                    handleNetworkError()
                }
                // Check if API is not yet implemented (beta/unsupported region)
                else if (errorMessage.contains("not yet implemented") ||
                         errorMessage.contains("not implemented")) {
                    Log.w(TAG, "Age Signals API not yet implemented - allowing access (API active Jan 1, 2026)")
                    // API not ready yet in this region, allow access
                    proceedToApp()
                }
                // Other errors - retry but ultimately block access
                else {
                    handleVerificationError(
                        "Age verification failed: ${exception.message}",
                        isRetryable = true
                    )
                }
            }
    }

    @Suppress("CAST_NEVER_SUCCEEDS")
    private fun handleAgeSignalsResult(result: AgeSignalsResult) {
        // Note: userStatus() returns an @IntDef annotated value
        // Cast to Int for comparison (despite Kotlin warning, this works at runtime)
        val statusValue = result.userStatus() as? Int ?: -1
        val ageLower = result.ageLower()
        val ageUpper = result.ageUpper()

        Log.d(TAG, "Age signals result - userStatus: $statusValue, ageLower: $ageLower, ageUpper: $ageUpper")

        // Check if user meets age requirement (18+)
        // Status values: VERIFIED=0, SUPERVISED=1, SUPERVISED_APPROVAL_PENDING=2, SUPERVISED_APPROVAL_DENIED=3, UNKNOWN=4
        val isEligible = when {
            // VERIFIED status (0) means user is over 18
            statusValue == 0 -> true  // VERIFIED

            // For supervised accounts or other statuses, check age range
            // ageLower returns primitive int, -1 indicates no value
            ageLower >= 18 -> true

            // If age signals are not available (both are -1), we might be in an unsupported region
            ageLower == -1 && ageUpper == -1 -> {
                Log.w(TAG, "Age signals returned no age range - might be unsupported region")
                // In unsupported regions, we allow access (API only active in specific jurisdictions)
                true
            }

            else -> false
        }

        if (isEligible) {
            Log.d(TAG, "User meets age requirement, proceeding to app")
            proceedToApp()
        } else {
            Log.w(TAG, "User does not meet age requirement (must be 18+)")
            showAgeRestrictionDialog()
        }
    }

    private fun handleNetworkError() {
        Log.e(TAG, "Network error - age data not cached, internet required")

        binding.verificationProgress.visibility = View.GONE

        if (retryAttempts < maxRetryAttempts) {
            retryAttempts++
            binding.verificationMessage.text =
                "No internet connection.\n\nAge verification requires an internet connection.\n\nRetrying automatically... (Attempt $retryAttempts/$maxRetryAttempts)"

            // Retry after delay
            lifecycleScope.launch {
                delay(3000) // Wait 3 seconds before retry
                checkAgeSignals()
            }
        } else {
            // Max retries reached - require user to connect and retry manually
            binding.verificationMessage.text =
                "No internet connection.\n\nThis app requires age verification, which needs an internet connection.\n\nPlease connect to the internet and tap Retry."
            binding.retryButton.visibility = View.VISIBLE
            Toast.makeText(this, "Internet connection required for age verification", Toast.LENGTH_LONG).show()
        }
    }

    private fun handleVerificationError(errorMessage: String, isRetryable: Boolean) {
        Log.e(TAG, "Verification error: $errorMessage (retryable: $isRetryable)")

        binding.verificationProgress.visibility = View.GONE

        if (isRetryable && retryAttempts < maxRetryAttempts) {
            retryAttempts++
            binding.verificationMessage.text = "$errorMessage\n\nRetrying automatically... (Attempt $retryAttempts/$maxRetryAttempts)"

            // Retry after delay
            lifecycleScope.launch {
                delay(2000) // Wait 2 seconds before retry
                checkAgeSignals()
            }
        } else {
            // Max retries reached or non-retryable error
            binding.verificationMessage.text = "$errorMessage\n\nPlease check your connection and try again."
            binding.retryButton.visibility = View.VISIBLE
            Toast.makeText(this, "Age verification failed", Toast.LENGTH_LONG).show()
        }
    }

    private fun showAgeRestrictionDialog() {
        binding.verificationProgress.visibility = View.GONE
        binding.verificationMessage.text = "This app is restricted to users 18 years of age and older.\n\nYou do not meet the age requirement to use this application."

        Toast.makeText(
            this,
            "Age restriction: You must be 18 or older to use this app",
            Toast.LENGTH_LONG
        ).show()

        // Don't show retry button as age is verified, just not eligible
        // User should exit the app

        // Finish activity after a delay to let user read the message
        lifecycleScope.launch {
            delay(3000)
            finishAffinity() // Close all activities and exit app
        }
    }

    private fun proceedToApp() {
        // Age verification passed, proceed to MainActivity
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish() // Don't allow back navigation to verification screen
    }

    override fun onBackPressed() {
        // Prevent back button during age verification
        // User must either pass verification or exit the app
    }

    companion object {
        private const val TAG = "AgeVerification"
    }
}
