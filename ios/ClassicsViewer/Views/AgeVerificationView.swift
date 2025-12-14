import SwiftUI
import DeclaredAgeRange

// Age verification view using Apple's DeclaredAgeRange API (iOS 26+)
// Blocks access unless user is verified as 18+

struct AgeVerificationView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.requestAgeRange) private var requestAgeRange

    @State private var isVerifying = true
    @State private var errorMessage: String?
    @State private var showRetryButton = false
    @State private var retryCount = 0
    @State private var isBlocked = false
    private let maxRetries = 3

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 20) {
                Spacer()

                Text("Age Verification")
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundColor(.white)

                if isVerifying {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(1.5)
                        .padding()

                    Text("Verifying age requirements...\nThis app is only available for users 18 and older.")
                        .multilineTextAlignment(.center)
                        .foregroundColor(.white)
                        .padding()
                } else if let error = errorMessage {
                    Text(error)
                        .multilineTextAlignment(.center)
                        .foregroundColor(.white)
                        .padding()

                    if showRetryButton {
                        Button(action: {
                            retryCount = 0
                            checkAge()
                        }) {
                            Text("Retry")
                                .fontWeight(.semibold)
                                .foregroundColor(.black)
                                .padding(.horizontal, 40)
                                .padding(.vertical, 12)
                                .background(Color.white)
                                .cornerRadius(8)
                        }
                        .padding(.top, 20)
                    }
                }

                Spacer()
            }
            .padding()
        }
        .onAppear {
            checkAge()
        }
    }

    private func checkAge() {
        isVerifying = true
        errorMessage = nil
        showRetryButton = false
        isBlocked = false

        Task {
            await performAgeCheck()
        }
    }

    @MainActor
    private func performAgeCheck() async {
        NSLog("AgeVerification: Starting age check")

        do {
            // Request age range with 18 as the gate
            let response = try await requestAgeRange(ageGates: 18)

            switch response {
            case .declinedSharing:
                // User declined to share age - block access
                NSLog("AgeVerification: User declined to share age - blocking access")
                showAgeRestriction(message: "Age verification is required to use this app.\n\nThis app contains classical texts that may include mature themes and is restricted to users 18 years of age and older.\n\nYou must share your age range to continue.")

            case .sharing(let range):
                // Check if user is 18+
                if let lowerBound = range.lowerBound, lowerBound >= 18 {
                    NSLog("AgeVerification: User verified as 18+ (lowerBound: \(lowerBound))")
                    proceedToApp()
                } else {
                    // User is under 18
                    let ageInfo = "lowerBound: \(range.lowerBound ?? -1), upperBound: \(range.upperBound ?? -1)"
                    NSLog("AgeVerification: User is under 18 (\(ageInfo)) - blocking access")
                    showAgeRestriction(message: "This app is restricted to users 18 years of age and older.\n\nYou do not meet the age requirement to use this application.")
                }
            }
        } catch {
            NSLog("AgeVerification: Error checking age: \(error.localizedDescription)")
            handleError(error)
        }
    }

    @MainActor
    private func handleError(_ error: Error) {
        if retryCount < maxRetries {
            retryCount += 1
            NSLog("AgeVerification: Retrying (\(retryCount)/\(maxRetries))...")

            // Retry after delay
            Task {
                try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
                await performAgeCheck()
            }
        } else {
            // Max retries reached - show error with retry option
            // Do NOT allow access without verification
            isVerifying = false
            errorMessage = "Age verification failed.\n\nThis app requires age verification to comply with content regulations.\n\nPlease ensure you are signed into iCloud and try again.\n\nError: \(error.localizedDescription)"
            showRetryButton = true
            isBlocked = true
        }
    }

    @MainActor
    private func showAgeRestriction(message: String) {
        isVerifying = false
        errorMessage = message
        showRetryButton = false
        isBlocked = true
        // User cannot proceed - they must close the app
    }

    @MainActor
    private func proceedToApp() {
        isVerifying = false
        appState.isAgeVerified = true
    }
}

// MARK: - Preview

struct AgeVerificationView_Previews: PreviewProvider {
    static var previews: some View {
        AgeVerificationView()
            .environmentObject(AppState())
    }
}
