package com.classicsviewer.app

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
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
 * **This is not the app's primary 18+ control.** That is Play Console's Restrict Minor Access,
 * enabled since 2025-08-07, which stops minors searching for, downloading, or purchasing the app
 * worldwide - before any of this code runs. Everyone reaching this screen already passed that.
 *
 * This activity's job is therefore narrow: act on what Play *asserts*, and nothing more. It does
 * not attempt to establish an age Play has not reported, because the app has no means of doing so.
 * A self-declared date of birth shipped in 0.8.134 and was removed in 0.8.135: it stops only honest
 * minors, who were already stopped at the store, while costing either persisted state (forbidden,
 * see CLAUDE.md) or a prompt on every single launch.
 *
 *  - Play reports a range >= [MINIMUM_AGE]  -> access granted.
 *  - Play reports a range <  [MINIMUM_AGE]  -> denied, authoritatively, terminal. No override.
 *  - VERIFICATION_REQUIRED -> denied, with a route into Play. Play has identified the user as
 *    being in a jurisdiction where verification is legally mandatory; that denial is meaningful
 *    and is the user's to clear.
 *  - APP_NOT_OWNED / SDK_VERSION_OUTDATED -> denied. Structural problems with the install; this
 *    is also what stops a sideloaded release build.
 *  - Anything else (NOT_SHARED, no age range, unrecognised status, unrecoverable errors) means
 *    Play produced no information. Access is granted, because the store-level gate already
 *    applied and nothing here can add to it.
 *
 * That last case is the common one, not an edge case: Play returns signals only in Brazil and a
 * few US states, and even inside a covered state only for accounts created after the cutoff.
 * Denying on it - as 0.8.131-0.8.133 did - locks out essentially the entire audience while
 * identifying no additional minor.
 *
 * [BuildConfig.DEBUG] additionally bypasses the gate for sideloaded builds, which are not owned by
 * Play and can never obtain signals. Release builds have no bypass.
 *
 * Nothing is cached or persisted. The age range, its source, and the install id are read, used to
 * make one decision, and discarded; every launch asks Play afresh. There is deliberately no
 * "already verified" flag and no stored age of any kind. Do not add one.
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

        binding.playStoreButton.setOnClickListener {
            openPlayStore()
        }

        startVerification()
    }

    /**
     * Creates the manager on first use, then runs the check. The listener is wired before this
     * runs so the Retry button stays functional even when manager creation is what failed.
     */
    private fun startVerification() {
        if (!::ageSignalsManager.isInitialized) {
            try {
                ageSignalsManager = AgeSignalsManagerFactory.create(applicationContext)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to create AgeSignalsManager", e)
                // Play can never answer on this device. An absence of information, not evidence
                // the user is under age.
                proceedWithoutSignal("manager unavailable")
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

                    // Ambiguous by design. Google documents this as covering "user didn't share
                    // age range, parent rejected the request, or not eligible" - and "not
                    // eligible" is every account outside the rollout, including accounts inside a
                    // covered state that predate its cutoff. It carries no evidence about age.
                    AgeSignalsStatus.NOT_SHARED -> proceedWithoutSignal("NOT_SHARED")

                    // The one status that is genuinely informative without being an age range:
                    // Play is telling us this user is somewhere verification is mandatory and has
                    // not completed it. Denial here is meaningful, and the user can clear it.
                    AgeSignalsStatus.VERIFICATION_REQUIRED -> denyFinal(
                        "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                            "Google Play requires you to verify your age before it can confirm this.\n\n" +
                            "Tap Open Google Play to verify (you may be asked for ID, a card, or a " +
                            "selfie), then return here and tap Retry.",
                        allowRetry = true,
                        showPlayStore = true
                    )

                    // UNSPECIFIED or a value added by a future SDK: no usable signal either way.
                    else -> proceedWithoutSignal("status $status")
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

        if (ageLower != null && ageLower >= MINIMUM_AGE) {
            Log.d(TAG, "Age requirement met, proceeding to app")
            proceedToApp()
            return
        }

        if (ageLower == null) {
            // Access was granted but no range came back. Again an absence of information.
            Log.w(TAG, "No age range returned")
            proceedWithoutSignal("no age range")
            return
        }

        // The one place the app has positive evidence the user is under age. Terminal.
        Log.w(TAG, "Age requirement not met - denying access")
        denyFinal(
            "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                "You do not meet the age requirement to use this application.",
            allowRetry = false,
            // Matches 0.8.130: a confirmed under-age result closes the app rather than leaving
            // the user on a screen they can re-trigger checks from.
            exitApp = true
        )
    }

    /**
     * Maps an API failure to an outcome. [retryAction] re-runs only the step that failed.
     *
     * Only two error codes are terminal denials. The rest describe a broken or unavailable Play
     * connection, which says nothing about the user's age, so after bounded retries they defer to
     * the store-level gate rather than locking the user out.
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
            // Terminal: the app must be installed by Play for signals to be available. This is
            // also what prevents a sideloaded release build from reaching the app.
            AgeSignalsErrorCode.APP_NOT_OWNED -> denyFinal(
                "Age verification is required to use this app.\n\n" +
                    "This copy was not installed by Google Play. Please install the app from Google Play.",
                allowRetry = false
            )

            // Terminal: this app ships an SDK version Play no longer supports.
            AgeSignalsErrorCode.SDK_VERSION_OUTDATED -> denyFinal(
                "Age verification is required to use this app.\n\n" +
                    "This version of the app is out of date. Please update it from Google Play.",
                allowRetry = false
            )

            AgeSignalsErrorCode.NETWORK_ERROR -> retryThenProceed(
                "Checking age requirements requires an internet connection.",
                retryAction
            )

            AgeSignalsErrorCode.PLAY_STORE_NOT_FOUND,
            AgeSignalsErrorCode.PLAY_SERVICES_NOT_FOUND,
            AgeSignalsErrorCode.API_NOT_AVAILABLE,
            AgeSignalsErrorCode.PLAY_STORE_VERSION_OUTDATED,
            AgeSignalsErrorCode.PLAY_SERVICES_VERSION_OUTDATED,
            AgeSignalsErrorCode.CANNOT_BIND_TO_SERVICE,
            AgeSignalsErrorCode.CLIENT_TRANSIENT_ERROR,
            AgeSignalsErrorCode.INTERNAL_ERROR -> retryThenProceed(
                "Age requirements could not be checked with Google Play.",
                retryAction
            )

            // Unknown error code, or an exception that is not an AgeSignalsException.
            else -> retryThenProceed(
                "Age requirements could not be checked with Google Play.",
                retryAction
            )
        }
    }

    /** Auto-retries a transient failure a bounded number of times, then defers to the store gate. */
    private fun retryThenProceed(message: String, retryAction: () -> Unit) {
        if (retryAttempts < MAX_RETRY_ATTEMPTS) {
            retryAttempts++
            binding.verificationProgress.visibility = View.VISIBLE
            binding.retryButton.visibility = View.GONE
            binding.playStoreButton.visibility = View.GONE
            binding.verificationMessage.text =
                "$message\n\nRetrying... (Attempt $retryAttempts/$MAX_RETRY_ATTEMPTS)"

            lifecycleScope.launch {
                delay(RETRY_DELAY_MS)
                retryAction()
            }
        } else {
            proceedWithoutSignal("retries exhausted")
        }
    }

    /**
     * Play produced no usable information about this user.
     *
     * Access is granted, because Restrict Minor Access has already gated acquisition at the store
     * and there is nothing further this app can establish. This is not a weakening of the age
     * requirement - it is declining to deny an audience the API was never able to describe.
     */
    private fun proceedWithoutSignal(reason: String) {
        Log.d(TAG, "No usable Play age signal ($reason) - deferring to store-level restriction")
        proceedToApp()
    }

    /**
     * Sends the user to Google Play so they can resolve a VERIFICATION_REQUIRED status.
     *
     * Google documents no deep link to the age verification flow itself, so this opens this app's
     * store listing - the place Play surfaces the age check for an age-restricted title - and falls
     * back to the Play Store's own launcher entry if that cannot be resolved.
     */
    private fun openPlayStore() {
        val listing = Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$packageName"))
        try {
            startActivity(listing)
            return
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "Could not open Play Store listing", e)
        }

        val playStore = packageManager.getLaunchIntentForPackage(PLAY_STORE_PACKAGE)
        if (playStore != null) {
            startActivity(playStore)
        } else {
            Log.w(TAG, "Play Store is not installed; cannot direct user to verification")
            binding.verificationMessage.text =
                "The Google Play Store is not available on this device, so your age cannot be " +
                    "verified. Install or enable the Play Store, then tap Retry."
            binding.playStoreButton.visibility = View.GONE
        }
    }

    private fun showChecking() {
        binding.verificationProgress.visibility = View.VISIBLE
        binding.retryButton.visibility = View.GONE
        binding.playStoreButton.visibility = View.GONE
        binding.verificationMessage.text =
            "Checking age requirements...\nThis app is only available for users $MINIMUM_AGE and older."
    }

    /**
     * Terminal denial. There is no path to MainActivity from here.
     *
     * @param allowRetry shows a Retry button that re-runs the full check, so the user can act on
     *   the remediation described in [message].
     * @param exitApp closes the app after [EXIT_DELAY_MS] instead of leaving the user on this
     *   screen. Used for a confirmed under-age result, matching 0.8.130 behaviour.
     * @param showPlayStore offers a route into Google Play, for denials the user can clear there.
     */
    private fun denyFinal(
        message: String,
        allowRetry: Boolean,
        exitApp: Boolean = false,
        showPlayStore: Boolean = false,
    ) {
        binding.verificationProgress.visibility = View.GONE
        binding.verificationMessage.text = message
        binding.retryButton.visibility = if (allowRetry) View.VISIBLE else View.GONE
        binding.playStoreButton.visibility = if (showPlayStore) View.VISIBLE else View.GONE

        if (exitApp) {
            lifecycleScope.launch {
                delay(EXIT_DELAY_MS) // let the user read the message first
                finishAffinity()
            }
        }
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
        private const val PLAY_STORE_PACKAGE = "com.android.vending"
        private const val MAX_RETRY_ATTEMPTS = 3
        private const val RETRY_DELAY_MS = 2000L
        private const val EXIT_DELAY_MS = 3000L
    }
}
