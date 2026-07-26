package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.databinding.ActivityAgeVerificationBinding
import com.classicsviewer.app.utils.PreferencesManager
import com.google.android.gms.tasks.Task
import com.google.android.play.agesignals.AgeSignalsAccessRequest
import com.google.android.play.agesignals.AgeSignalsException
import com.google.android.play.agesignals.AgeSignalsManager
import com.google.android.play.agesignals.AgeSignalsManagerFactory
import com.google.android.play.agesignals.AgeSignalsRequest
import com.google.android.play.agesignals.AgeSignalsResult
import com.google.android.play.agesignals.model.AgeSignalsErrorCode
import com.google.android.play.agesignals.model.AgeSignalsStatus
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
        // Enable edge-to-edge display for Android 15+ compatibility
        enableEdgeToEdge()

        super.onCreate(savedInstanceState)
        binding = ActivityAgeVerificationBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Apply window insets to avoid content being hidden behind system bars
        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

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

        // age-signals 0.0.4 introduces a two-step flow: first request access,
        // which surfaces the Play in-app age-range sharing prompt when needed,
        // then read the age signals themselves via checkAgeSignals().
        val accessRequest = AgeSignalsAccessRequest.builder()
            .setActivity(this)
            .build()

        ageSignalsManager.requestAgeSignalsAccess(accessRequest)
            .addOnSuccessListener { accessResult ->
                val status = accessResult.ageSignalsStatus() ?: AgeSignalsStatus.UNSPECIFIED
                Log.d(TAG, "Age signals access status: $status")
                // Proceed to read the age range regardless of share status. When the
                // user has not shared signals (or none are available) checkAgeSignals
                // returns no age range, which is handled permissively in
                // handleAgeSignalsResult, matching prior behavior.
                fetchAgeSignals()
            }
            .addOnFailureListener { exception ->
                handleAgeSignalsFailure(exception)
            }
    }

    private fun fetchAgeSignals() {
        val request = AgeSignalsRequest.builder().build()

        ageSignalsManager.checkAgeSignals(request)
            .addOnSuccessListener { result ->
                handleAgeSignalsResult(result)
            }
            .addOnFailureListener { exception ->
                handleAgeSignalsFailure(exception)
            }
    }

    private fun handleAgeSignalsFailure(exception: Exception) {
        Log.e(TAG, "Age signals check failed", exception)

        // Check error code if this is an AgeSignalsException
        val errorCode = (exception as? AgeSignalsException)?.errorCode
        Log.d(TAG, "Age signals error code: $errorCode")

        when (errorCode) {
            // Network error - block access until connected
            AgeSignalsErrorCode.NETWORK_ERROR -> {
                Log.e(TAG, "Network error during age verification - blocking access until connected")
                handleNetworkError()
            }
            // Service binding failed - expected for debug builds not from Play Store
            AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE -> {
                Log.w(TAG, "Cannot bind to Play Store service - allowing access (debug build or sideloaded)")
                proceedToApp()
            }
            // App not installed from Play Store
            AgeSignalsErrorCode.APP_NOT_OWNED -> {
                Log.w(TAG, "App not installed from Play Store - allowing access")
                proceedToApp()
            }
            // API not available in this region
            AgeSignalsErrorCode.API_NOT_AVAILABLE -> {
                Log.w(TAG, "Age Signals API not available - allowing access (unsupported region)")
                proceedToApp()
            }
            // Play Store or Play Services issues - allow access but log
            AgeSignalsErrorCode.PLAY_STORE_NOT_FOUND,
            AgeSignalsErrorCode.PLAY_SERVICES_NOT_FOUND,
            AgeSignalsErrorCode.PLAY_STORE_VERSION_OUTDATED,
            AgeSignalsErrorCode.PLAY_SERVICES_VERSION_OUTDATED -> {
                Log.w(TAG, "Play Store/Services issue (code $errorCode) - allowing access")
                proceedToApp()
            }
            // Transient errors - retry
            AgeSignalsErrorCode.CLIENT_TRANSIENT_ERROR -> {
                handleVerificationError(
                    "Age verification failed: ${exception.message}",
                    isRetryable = true
                )
            }
            // Unknown error code or not an AgeSignalsException - check message
            else -> {
                val errorMessage = exception.message?.lowercase() ?: ""
                if (errorMessage.contains("not yet implemented") ||
                    errorMessage.contains("not implemented")) {
                    Log.w(TAG, "Age Signals API not yet implemented - allowing access (API active Jan 1, 2026)")
                    proceedToApp()
                } else {
                    handleVerificationError(
                        "Age verification failed: ${exception.message}",
                        isRetryable = true
                    )
                }
            }
        }
    }

    private fun handleAgeSignalsResult(result: AgeSignalsResult) {
        // As of age-signals 0.0.4, userStatus() was removed. Eligibility is now
        // determined from the returned age range (ageLower/ageUpper); ageRangeSource
        // indicates how that range was established (UNSPECIFIED/TIER_A..TIER_D).
        val ageLower: Int? = result.ageLower()
        val ageUpper: Int? = result.ageUpper()
        val ageRangeSource: Int? = result.ageRangeSource()

        Log.d(TAG, "Age signals result - ageRangeSource: $ageRangeSource, ageLower: $ageLower, ageUpper: $ageUpper")

        // Check if user meets age requirement (18+)
        val isEligible = when {
            // Lower bound of the reported age range is 18 or above
            // ageLower/ageUpper return null when age data is not available
            ageLower != null && ageLower >= 18 -> true

            // If age signals are not available (both null), we might be in an unsupported region
            ageLower == null && ageUpper == null -> {
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
