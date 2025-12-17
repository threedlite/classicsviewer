import Foundation
import UIKit
import SwiftUI

/// Restarts the application after database changes
func restartApplication() {
    // On iOS, we can't truly restart the app like on Android
    // Instead, we'll reset the root view controller to force a fresh start

    // First, close the database connection
    Task {
        await DatabaseManagerAsync.shared.close()

        await MainActor.run {
            if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
               let window = windowScene.windows.first {

                // Clear user defaults for fresh start
                UserDefaults.standard.removeObject(forKey: "selectedLanguage")
                UserDefaults.standard.synchronize()

                // Clear any cached view models or state
                NotificationCenter.default.post(name: Notification.Name("DatabaseChanged"), object: nil)

                // Create a new app state and root view
                let newAppState = AppState()
                let newSearchContext = SearchNavigationContext()
                let contentView = ContentView()
                    .environmentObject(newAppState)
                    .environmentObject(newSearchContext)

                let newRootViewController = UIHostingController(rootView: contentView)

                // Animate the transition
                UIView.transition(with: window, duration: 0.5, options: .transitionCrossDissolve, animations: {
                    window.rootViewController = newRootViewController
                }, completion: { _ in
                    // Trigger database check
                    Task {
                        await newAppState.checkAndExtractDatabase()
                    }
                })

                window.makeKeyAndVisible()
            }
        }
    }
}