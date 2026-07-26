package com.classicsviewer.app

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import com.classicsviewer.app.databinding.ActivityAgeVerificationBinding
import com.classicsviewer.app.utils.PreferencesManager
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

/**
 * Age gate backed by the Play Age Signals API (com.google.android.play:age-signals:0.0.4).
 *
 * Policy is fail-closed: access is granted only when Play affirmatively reports an age range
 * whose lower bound is at least [MINIMUM_AGE]. Every other outcome - signals not shared,
 * verification required, no age range returned, or any API error - denies access. The app
 * cannot establish an age that Play does not report, so "unknown" is treated as "not eligible".
 *
 * The only exception is [BuildConfig.DEBUG]: sideloaded debug builds are not owned by Play and
 * can never obtain signals, so they bypass the gate to keep local development possible. Release
 * builds have no bypass.
 *
 * Nothing returned by the API is cached or persisted. The age range, its source, and the install
 * id are read, used to make one allow/deny decision, and discarded. There is deliberately no
 * "already verified" flag: every launch asks Play afresh. Do not add one.
 */
class AgeVerificationActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAgeVerificationBinding
    private lateinit var ageSignalsManager: AgeSignalsManager
    private var retryAttempts = 0

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

        binding.retryButton.setOnClickListener {
            retryAttempts = 0
            startVerification()
        }

        startVerification()
    }

    /**
     * Creates the manager on first use, then runs the check. Denies when the manager cannot be
     * created. The listener is wired before this runs so the Retry button stays functional even
     * when manager creation is what failed.
     */
    private fun startVerification() {
        if (!::ageSignalsManager.isInitialized) {
            try {
                ageSignalsManager = AgeSignalsManagerFactory.create(applicationContext)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create AgeSignalsManager", e)
                // No manager means no way to establish age. Deny, but let the user retry.
                denyRetryable("Age verification is unavailable on this device.")
                return
            }
        }

        requestAccess()
    }

    // Step 1 of the 0.0.4 flow. Surfaces Play's in-app age-sharing prompt when applicable and
    // reports whether signals are available to this app.
    private fun requestAccess() {
        showChecking()

        Log.d(TAG, "Requesting age signals access (attempt ${retryAttempts + 1}/$MAX_RETRY_ATTEMPTS)")

        val accessRequest = AgeSignalsAccessRequest.builder()
            .setActivity(this)
            .build()

        ageSignalsManager.requestAgeSignalsAccess(accessRequest)
            .addOnSuccessListener { accessResult ->
                val status = accessResult.ageSignalsStatus() ?: AgeSignalsStatus.UNSPECIFIED
                Log.d(TAG, "Age signals access status: $status")

                when (status) {
                    AgeSignalsStatus.SHARED -> fetchAgeSignals()

                    AgeSignalsStatus.NOT_SHARED -> denyFinal(
                        "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                            "Your age range has not been shared with this app, so access cannot be granted.\n\n" +
                            "You can change age sharing in the Google Play Store settings, then tap Retry.",
                        allowRetry = true
                    )

                    AgeSignalsStatus.VERIFICATION_REQUIRED -> denyFinal(
                        "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                            "Your age has not been verified with Google Play.\n\n" +
                            "Complete age verification in the Google Play Store, then tap Retry.",
                        allowRetry = true
                    )

                    // UNSPECIFIED or a value added by a future SDK: no usable signal, so deny.
                    else -> denyRetryable("Age verification returned an unrecognized status ($status).")
                }
            }
            .addOnFailureListener { exception ->
                handleFailure(exception) { requestAccess() }
            }
    }

    // Step 2. Only reached when access status is SHARED.
    private fun fetchAgeSignals() {
        val request = AgeSignalsRequest.builder().build()

        ageSignalsManager.checkAgeSignals(request)
            .addOnSuccessListener { result ->
                handleAgeSignalsResult(result)
            }
            .addOnFailureListener { exception ->
                // Access already succeeded; retry only this step so Play's consent prompt is
                // not re-triggered repeatedly.
                handleFailure(exception) { fetchAgeSignals() }
            }
    }

    private fun handleAgeSignalsResult(result: AgeSignalsResult) {
        val ageLower: Int? = result.ageLower()
        val ageUpper: Int? = result.ageUpper()
        val ageRangeSource: Int? = result.ageRangeSource()

        // The values returned by Play are never persisted and never leave this method. They are
        // written to the log only in debug builds; release builds log the decision, not the data.
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Age signals result - ageRangeSource: $ageRangeSource, ageLower: $ageLower, ageUpper: $ageUpper")
        }

        // The single grant condition: Play reports a range starting at or above the minimum age.
        // A null lower bound carries no age information and is therefore not eligible.
        if (ageLower != null && ageLower >= MINIMUM_AGE) {
            Log.d(TAG, "Age requirement met, proceeding to app")
            proceedToApp()
            return
        }

        if (ageLower == null) {
            Log.w(TAG, "No age range returned - denying access")
            denyFinal(
                "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                    "Google Play did not provide an age range for this account, so access cannot be granted.",
                allowRetry = true
            )
        } else {
            Log.w(TAG, "Age requirement not met - denying access")
            denyFinal(
                "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                    "You do not meet the age requirement to use this application.",
                allowRetry = false,
                // Matches 0.8.130: a confirmed under-age result closes the app rather than
                // leaving the user on a screen they can re-trigger checks from.
                exitApp = true
            )
        }
    }

    /**
     * Maps an API failure to a denial. No branch here grants access in a release build.
     * [retryAction] re-runs only the step that failed.
     */
    private fun handleFailure(exception: Exception, retryAction: () -> Unit) {
        val errorCode = (exception as? AgeSignalsException)?.errorCode
        Log.e(TAG, "Age signals call failed (errorCode: $errorCode)", exception)

        // Debug builds are sideloaded and are not owned by Play, so signals are unobtainable and
        // the gate is untestable locally. Release builds never take this branch: BuildConfig.DEBUG
        // is a compile-time false, so R8 removes it entirely.
        if (BuildConfig.DEBUG &&
            (errorCode == AgeSignalsErrorCode.APP_NOT_OWNED ||
                errorCode == AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE)
        ) {
            Log.w(TAG, "DEBUG build: bypassing age gate for errorCode $errorCode")
            proceedToApp()
            return
        }

        when (errorCode) {
            // Not retryable: the app must be reinstalled from Play for signals to be available.
            AgeSignalsErrorCode.APP_NOT_OWNED -> denyFinal(
                "Age verification is required to use this app.\n\n" +
                    "This copy was not installed by Google Play. Please install the app from Google Play.",
                allowRetry = false
            )

            // Not retryable: this app ships an SDK version Play no longer supports.
            AgeSignalsErrorCode.SDK_VERSION_OUTDATED -> denyFinal(
                "Age verification is required to use this app.\n\n" +
                    "This version of the app is out of date. Please update it from Google Play.",
                allowRetry = false
            )

            AgeSignalsErrorCode.NETWORK_ERROR -> retryOrDeny(
                "Age verification requires an internet connection.",
                retryAction
            )

            AgeSignalsErrorCode.PLAY_STORE_NOT_FOUND -> retryOrDeny(
                "Age verification requires the Google Play Store.\n\n" +
                    "Please install or enable the Play Store.",
                retryAction
            )

            AgeSignalsErrorCode.PLAY_SERVICES_NOT_FOUND -> retryOrDeny(
                "Age verification requires Google Play services.\n\n" +
                    "Please install or enable Google Play services.",
                retryAction
            )

            AgeSignalsErrorCode.API_NOT_AVAILABLE,
            AgeSignalsErrorCode.PLAY_STORE_VERSION_OUTDATED -> retryOrDeny(
                "Age verification requires a newer version of the Google Play Store.\n\n" +
                    "Please update the Play Store.",
                retryAction
            )

            AgeSignalsErrorCode.PLAY_SERVICES_VERSION_OUTDATED -> retryOrDeny(
                "Age verification requires a newer version of Google Play services.\n\n" +
                    "Please update Google Play services.",
                retryAction
            )

            AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE,
            AgeSignalsErrorCode.CLIENT_TRANSIENT_ERROR,
            AgeSignalsErrorCode.INTERNAL_ERROR -> retryOrDeny(
                "Age verification could not be completed.",
                retryAction
            )

            // Unknown error code, or an exception that is not an AgeSignalsException.
            else -> retryOrDeny(
                "Age verification could not be completed.",
                retryAction
            )
        }
    }

    /** Auto-retries a transient failure a bounded number of times, then denies with a Retry button. */
    private fun retryOrDeny(message: String, retryAction: () -> Unit) {
        if (retryAttempts < MAX_RETRY_ATTEMPTS) {
            retryAttempts++
            binding.verificationProgress.visibility = View.VISIBLE
            binding.retryButton.visibility = View.GONE
            binding.verificationMessage.text =
                "$message\n\nRetrying... (Attempt $retryAttempts/$MAX_RETRY_ATTEMPTS)"

            lifecycleScope.launch {
                delay(RETRY_DELAY_MS)
                retryAction()
            }
        } else {
            denyFinal("$message\n\nAccess cannot be granted until age verification succeeds.", allowRetry = true)
        }
    }

    private fun denyRetryable(message: String) {
        denyFinal("$message\n\nAccess cannot be granted until age verification succeeds.", allowRetry = true)
    }

    /**
     * Terminal denial. There is no path to MainActivity from here.
     *
     * @param allowRetry shows a Retry button that re-runs the full check, so the user can act on
     *   the remediation described in [message].
     * @param exitApp closes the app after [EXIT_DELAY_MS] instead of leaving the user on this
     *   screen. Used for a confirmed under-age result, matching 0.8.130 behaviour.
     */
    private fun denyFinal(message: String, allowRetry: Boolean, exitApp: Boolean = false) {
        binding.verificationProgress.visibility = View.GONE
        binding.verificationMessage.text = message
        binding.retryButton.visibility = if (allowRetry) View.VISIBLE else View.GONE

        if (exitApp) {
            lifecycleScope.launch {
                delay(EXIT_DELAY_MS) // let the user read the message first
                finishAffinity()
            }
        }
    }

    private fun showChecking() {
        binding.verificationProgress.visibility = View.VISIBLE
        binding.retryButton.visibility = View.GONE
        binding.verificationMessage.text =
            "Verifying age requirements...\nThis app is only available for users $MINIMUM_AGE and older."
    }

    private fun proceedToApp() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish() // Don't allow back navigation to verification screen
    }

    override fun onBackPressed() {
        // Prevent back button from dismissing the gate on OS versions that still route here.
        // The activity is the launcher and never starts MainActivity unless verification passed,
        // so finishing early cannot expose app content.
    }

    companion object {
        private const val TAG = "AgeVerification"
        private const val MINIMUM_AGE = 18
        private const val MAX_RETRY_ATTEMPTS = 3
        private const val RETRY_DELAY_MS = 2000L
        private const val EXIT_DELAY_MS = 3000L
    }
}
