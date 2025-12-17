import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @State private var hasStartedCheck = false

    var body: some View {
        Group {
            if !hasStartedCheck {
                // Show immediate loading indicator
                VStack {
                    Spacer()
                    ProgressView()
                        .scaleEffect(2)
                    Text("Starting ClassicsViewer...")
                        .padding()
                    Spacer()
                }
                .onAppear {
                    hasStartedCheck = true
                }
            } else if appState.needsRestart {
                VStack {
                    Spacer()
                    ProgressView()
                        .scaleEffect(2)
                    Text("Restarting with new database...")
                        .padding()
                    Spacer()
                }
                .onAppear {
                    // Force app to restart by resetting state
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                        appState.isDatabaseReady = false
                        appState.databaseManagersInitialized = false
                        appState.selectedLanguage = nil
                        appState.needsRestart = false
                        // Database check will be handled by app lifecycle
                    }
                }
            } else if appState.isExtracting {
                DatabaseExtractionView()
            } else if !appState.isDatabaseReady {
                VStack {
                    Spacer()
                    ProgressView()
                        .scaleEffect(2)
                    Text("Checking database...")
                        .padding()
                    Spacer()
                }
                .task {
                    await appState.checkAndExtractDatabase()
                }
            } else if !appState.databaseManagersInitialized {
                VStack {
                    Spacer()
                    ProgressView()
                        .scaleEffect(2)
                    Text("Initializing database...")
                        .padding()
                    Spacer()
                }
                .task {
                    await initializeDatabaseManagers()
                }
            } else if appState.selectedLanguage == nil {
                LanguageSelectionView()
            } else {
                MainNavigationView()
            }
        }
    }

    private func initializeDatabaseManagers() async {
        do {
            try await DatabaseManagerAsync.shared.initialize()
            try await UserDatabaseManagerAsync.shared.initialize()
            try await DefaultAudioExtractor.shared.ensureDefaultAudioExtracted()
        } catch {
            print("Failed to initialize database managers: \(error)")
        }
        appState.databaseManagersInitialized = true
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
            .environmentObject(AppState())
    }
}