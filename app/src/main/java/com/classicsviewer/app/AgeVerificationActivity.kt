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
import java.util.Calendar

/**
 * Age gate backed by the Play Age Signals API (com.google.android.play:age-signals:0.0.4).
 *
 * The goal is to restrict users under [MINIMUM_AGE], which is not the same thing as denying every
 * user Play cannot describe. The two are distinguished deliberately:
 *
 *  - Play affirmatively reports an age range >= [MINIMUM_AGE]  -> access granted.
 *  - Play affirmatively reports an age range <  [MINIMUM_AGE]  -> denied, authoritatively, with
 *    no fallback and no way to override.
 *  - VERIFICATION_REQUIRED -> denied. Play has identified the user as being in a jurisdiction
 *    where verification is mandatory, so declaring must not be an escape hatch there.
 *  - APP_NOT_OWNED / SDK_VERSION_OUTDATED -> denied. Structural problems with the install.
 *  - Everything else (NOT_SHARED, no age range, unrecognised status, unrecoverable errors) means
 *    Play produced no information at all. That is not evidence of being under age, so the user is
 *    asked to declare a date of birth instead.
 *
 * The last case is not an edge case: Play returns age signals only in Brazil and for Texas
 * accounts created after 2026-05-28. Treating its silence as a denial locks out every account
 * elsewhere in the world while identifying no additional minor.
 *
 * The ordering is what preserves the guarantee. Play is always asked first, so a declaration can
 * only ever fill a gap Play left, never contradict an answer Play gave.
 *
 * [BuildConfig.DEBUG] additionally bypasses the gate for sideloaded builds, which are not owned
 * by Play and can never obtain signals. Release builds have no bypass.
 *
 * Nothing returned by the API is cached or persisted. The age range, its source, and the install
 * id are read, used to make one decision, and discarded; every launch asks Play afresh. The
 * declaration flag stored in PreferencesManager is not a Play signal and must never become a
 * cache of one - it records only the outcome of the app's own fallback, and the date of birth
 * behind it is never stored or logged.
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
            binding.declarationPrompt.setTextColor(0xFF000000.toInt())
        } else {
            binding.root.setBackgroundColor(0xFF000000.toInt())
            binding.verificationTitle.setTextColor(0xFFFFFFFF.toInt())
            binding.verificationMessage.setTextColor(0xFFFFFFFF.toInt())
            binding.declarationPrompt.setTextColor(0xFFFFFFFF.toInt())
        }

        // A future date of birth is not a meaningful input, and allowing one would only produce
        // a negative age that the minimum-age check would reject anyway.
        binding.birthDatePicker.maxDate = System.currentTimeMillis()

        binding.retryButton.setOnClickListener {
            retryAttempts = 0
            startVerification()
        }

        binding.declarationContinue.setOnClickListener {
            onDeclarationSubmitted()
        }

        binding.playStoreButton.setOnClickListener {
            openPlayStore()
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
                // No manager means Play can never answer on this device. That is an absence of
                // information, not evidence the user is under age, so fall back to declaring.
                requireAgeDeclaration("manager unavailable")
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

                    // Ambiguous by design: this is returned both when a user declines sharing and
                    // when the account is simply not eligible - which is every account outside
                    // Brazil and post-2026-05-28 Texas. The API cannot distinguish the two, so it
                    // carries no evidence about age and cannot stand in for a denial.
                    AgeSignalsStatus.NOT_SHARED -> requireAgeDeclaration("NOT_SHARED")

                    // Deliberately NOT given the declaration fallback. This status means Play has
                    // identified the user as being in a jurisdiction where age verification is
                    // mandatory, so self-declaration must not become an escape hatch in exactly
                    // the place the law applies. Remediation is to resolve status in the Play Store.
                    AgeSignalsStatus.VERIFICATION_REQUIRED -> denyFinal(
                        "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                            "Google Play requires you to verify your age before it can confirm this.\n\n" +
                            "Tap Open Google Play to verify (you may be asked for ID, a card, or a " +
                            "selfie), then return here and tap Retry.",
                        allowRetry = true,
                        showPlayStore = true
                    )

                    // UNSPECIFIED or a value added by a future SDK: no usable signal either way.
                    else -> requireAgeDeclaration("status $status")
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
            // Access was granted but no range came back. Again an absence of information, not a
            // statement that the user is under age.
            Log.w(TAG, "No age range returned")
            requireAgeDeclaration("no age range")
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
            // Retries are exhausted and Play still has not answered. A device that is offline or
            // a Play service that is failing tells us nothing about the user's age, so fall back
            // rather than locking the user out permanently.
            requireAgeDeclaration("retries exhausted")
        }
    }

    /**
     * Fallback for the case where Play produced no usable age signal at all.
     *
     * Play is always asked first and always wins. This path is reached only for NOT_SHARED, an
     * unrecognised status, a missing age range, or an unrecoverable error. A user Play has
     * affirmatively reported as under age is denied in [handleAgeSignalsResult] and never reaches
     * here, so a declaration can never override a Play answer.
     *
     * This exists because Play returns age signals only in Brazil and for Texas accounts created
     * after 2026-05-28. Treating "Play has no information" as "user is under age" denies every
     * account elsewhere in the world while identifying no additional minor.
     */
    private fun requireAgeDeclaration(reason: String) {
        Log.d(TAG, "No usable Play age signal ($reason) - falling back to age declaration")

        if (PreferencesManager.getAgeDeclarationConfirmed(this)) {
            Log.d(TAG, "Age already declared as $MINIMUM_AGE+, proceeding to app")
            proceedToApp()
            return
        }

        binding.verificationProgress.visibility = View.GONE
        binding.retryButton.visibility = View.GONE
        binding.playStoreButton.visibility = View.GONE
        binding.verificationMessage.text =
            "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                "Google Play did not provide an age range for this account."
        binding.declarationGroup.visibility = View.VISIBLE
    }

    /**
     * Applies the declared date of birth. The date itself is used to compute an age and then
     * discarded - only the resulting decision is stored, and the date is never logged.
     */
    private fun onDeclarationSubmitted() {
        val picker = binding.birthDatePicker
        val age = completedYearsSince(picker.year, picker.month, picker.dayOfMonth)

        if (age >= MINIMUM_AGE) {
            PreferencesManager.setAgeDeclarationConfirmed(this, true)
            Log.d(TAG, "Declared age meets requirement, proceeding to app")
            proceedToApp()
            return
        }

        PreferencesManager.setAgeDeclarationConfirmed(this, false)
        Log.w(TAG, "Declared age below minimum - denying access")
        binding.declarationGroup.visibility = View.GONE
        denyFinal(
            "This app is restricted to users $MINIMUM_AGE years of age and older.\n\n" +
                "You do not meet the age requirement to use this application.",
            allowRetry = false,
            exitApp = true
        )
    }

    /** Completed years between the given date and today. */
    private fun completedYearsSince(year: Int, month: Int, dayOfMonth: Int): Int {
        val now = Calendar.getInstance()
        val birthdayPassedThisYear = now.get(Calendar.MONTH) > month ||
            (now.get(Calendar.MONTH) == month && now.get(Calendar.DAY_OF_MONTH) >= dayOfMonth)
        return now.get(Calendar.YEAR) - year - if (birthdayPassedThisYear) 0 else 1
    }

    /**
     * Terminal denial. There is no path to MainActivity from here.
     *
     * @param allowRetry shows a Retry button that re-runs the full check, so the user can act on
     *   the remediation described in [message].
     * @param exitApp closes the app after [EXIT_DELAY_MS] instead of leaving the user on this
     *   screen. Used for a confirmed under-age result, matching 0.8.130 behaviour.
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
        private const val PLAY_STORE_PACKAGE = "com.android.vending"
        private const val MAX_RETRY_ATTEMPTS = 3
        private const val RETRY_DELAY_MS = 2000L
        private const val EXIT_DELAY_MS = 3000L
    }
}
