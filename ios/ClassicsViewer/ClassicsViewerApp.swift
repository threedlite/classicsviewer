import SwiftUI

@main
struct ClassicsViewerApp: App {
    @StateObject private var appState = AppState()
    @StateObject private var databaseService = DatabaseService()
    @StateObject private var searchContext = SearchNavigationContext()

    var body: some Scene {
        WindowGroup {
            if !appState.isAgeVerified {
                // Age verification must pass before accessing the app
                AgeVerificationView()
                    .environmentObject(appState)
            } else if appState.isExtracting {
                DatabaseExtractionView()
                    .environmentObject(appState)
            } else if appState.isDatabaseReady && appState.databaseManagersInitialized && appState.selectedLanguage != nil {
                MainNavigationView()
                    .environmentObject(appState)
                    .environmentObject(searchContext)
            } else if appState.isDatabaseReady && appState.databaseManagersInitialized {
                LanguageSelectionView()
                    .environmentObject(appState)
                    .environmentObject(searchContext)
            } else {
                LoadingView(message: appState.initializationStatus)
                    .task {
                        // First check if database exists and extract if needed
                        appState.initializationStatus = "Checking database..."
                        print("DEBUG: Starting checkAndExtractDatabase")
                        await appState.checkAndExtractDatabase()
                        print("DEBUG: checkAndExtractDatabase completed, isDatabaseReady: \(appState.isDatabaseReady)")

                        // Then initialize the database service
                        if appState.isDatabaseReady {
                            do {
                                // Initialize the async database managers
                                appState.initializationStatus = "Initializing main database..."
                                print("DEBUG: About to initialize DatabaseManagerAsync")
                                try await DatabaseManagerAsync.shared.initialize()
                                print("Database manager initialized successfully")

                                // Initialize user database manager
                                appState.initializationStatus = "Initializing user database..."
                                NSLog("DEBUG: About to initialize UserDatabaseManagerAsync")
                                try await UserDatabaseManagerAsync.shared.initialize()
                                NSLog("DEBUG: UserDatabaseManagerAsync initialized successfully")
                                print("User database manager initialized successfully")

                                // Now extract default audio after user database is ready
                                appState.initializationStatus = "Checking for bundled audio..."
                                NSLog("DEBUG: Database managers ready, checking for bundled audio")
                                do {
                                    NSLog("DEBUG: About to call DefaultAudioExtractor.ensureDefaultAudioExtracted()")
                                    try await DefaultAudioExtractor.shared.ensureDefaultAudioExtracted()
                                    NSLog("DEBUG: DefaultAudioExtractor.ensureDefaultAudioExtracted() completed")
                                } catch {
                                    NSLog("ERROR: Failed to extract default audio: \(error)")
                                    NSLog("ERROR: Error details: \(String(describing: error))")
                                    // Continue anyway - audio is optional
                                }

                                // Mark managers as initialized
                                appState.initializationStatus = "Ready!"
                                appState.databaseManagersInitialized = true
                            } catch {
                                print("Failed to initialize database managers: \(error)")
                                // Still mark as initialized to allow app to continue
                                appState.databaseManagersInitialized = true
                            }
                        }
                    }
            }
        }
    }
}

@MainActor
class AppState: ObservableObject {
    @Published var isAgeVerified = false
    @Published var isDatabaseReady = false
    @Published var isExtracting = false
    @Published var extractionProgress: Double = 0.0
    @Published var selectedLanguage: Language?
    @Published var needsRestart = false
    @Published var databaseManagersInitialized = false
    @Published var initializationStatus = "Initializing..."
    
    enum Language: Equatable {
        case greek
        case latin
        case custom(String, String) // (id, displayName)

        var isGreek: Bool {
            switch self {
            case .greek:
                return true
            case .latin, .custom:
                return false
            }
        }

        var displayName: String {
            switch self {
            case .greek:
                return "Greek"
            case .latin:
                return "Latin"
            case .custom(_, let name):
                return name
            }
        }

        var id: String {
            switch self {
            case .greek:
                return "greek"
            case .latin:
                return "latin"
            case .custom(let id, _):
                return id
            }
        }
    }
    
    @MainActor
    func checkAndExtractDatabase() async {
        NSLog("DEBUG: checkAndExtractDatabase() START")
        let documentsPath = NSSearchPathForDirectoriesInDomains(.documentDirectory, .userDomainMask, true).first!

        // Check which database should be used based on user preference
        let useFullDatabase = UserDefaults.standard.useFullDatabase
        NSLog("DEBUG: useFullDatabase preference = \(useFullDatabase)")

        let databaseName = useFullDatabase ? "perseus_texts_full.db" : "perseus_texts.db"
        let dbPath = (documentsPath as NSString).appendingPathComponent(databaseName)

        NSLog("DEBUG: Target database: \(databaseName)")
        NSLog("DEBUG: Full path: \(dbPath)")

        // Also check what files exist
        let sampleExists = FileManager.default.fileExists(atPath: (documentsPath as NSString).appendingPathComponent("perseus_texts.db"))
        let fullExists = FileManager.default.fileExists(atPath: (documentsPath as NSString).appendingPathComponent("perseus_texts_full.db"))
        NSLog("DEBUG: Sample DB exists: \(sampleExists), Full DB exists: \(fullExists)")

        if FileManager.default.fileExists(atPath: dbPath) {
            NSLog("DEBUG: Target database exists, marking ready")
            isDatabaseReady = true
        } else if useFullDatabase {
            // Full database was activated but file doesn't exist - revert to sample
            NSLog("DEBUG: Full database file missing, reverting to sample database")
            UserDefaults.standard.useFullDatabase = false
            let sampleDbPath = (documentsPath as NSString).appendingPathComponent("perseus_texts.db")
            if FileManager.default.fileExists(atPath: sampleDbPath) {
                NSLog("DEBUG: Sample database exists after revert, ready to use")
                isDatabaseReady = true
            } else {
                NSLog("DEBUG: No sample database either, need to extract bundled database")
                isExtracting = true
                extractionProgress = 0.0
                await extractDatabaseAsync()
            }
        } else {
            NSLog("DEBUG: No database found at \(dbPath), need to extract bundled database")
            isExtracting = true
            extractionProgress = 0.0
            await extractDatabaseAsync()
        }

        NSLog("DEBUG: checkAndExtractDatabase() END - isDatabaseReady=\(isDatabaseReady), isExtracting=\(isExtracting)")
        // Audio extraction moved to after database managers are initialized
    }
    
    // Helper function for timeout
    private func withTimeout<T>(seconds: TimeInterval, operation: @escaping () async throws -> T) async throws -> T {
        try await withThrowingTaskGroup(of: T.self) { group in
            group.addTask {
                try await operation()
            }
            
            group.addTask {
                try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
                throw CancellationError()
            }
            
            let result = try await group.next()!
            group.cancelAll()
            return result
        }
    }
    
    @MainActor
    func extractDatabaseAsync() async {
        do {
            print("DEBUG: Starting database extraction...")
            // When extracting bundled database, clear any external database name
            UserDefaults.standard.removeObject(forKey: "externalDatabaseName")

            // Extract database using the proper extractor
            try await DatabaseExtractor.shared.extractBundledDatabase { progress in
                Task { @MainActor in
                    self.extractionProgress = progress
                }
            }

            print("Database extraction completed")

            // Extract default audio package if needed
            do {
                print("DEBUG: About to call DefaultAudioExtractor.ensureDefaultAudioExtracted() after DB extraction")
                try await DefaultAudioExtractor.shared.ensureDefaultAudioExtracted()
                print("DEBUG: DefaultAudioExtractor.ensureDefaultAudioExtracted() completed after DB extraction")
            } catch {
                print("ERROR: Failed to extract default audio after DB extraction: \(error)")
                print("ERROR: Error details: \(String(describing: error))")
                // Continue anyway - audio is optional
            }

            isDatabaseReady = true
            isExtracting = false
        } catch {
            print("ERROR: Database extraction failed: \(error)")
            // Mark as ready anyway to continue to language selection
            // User can import a database from Settings
            isExtracting = false
            isDatabaseReady = true // Allow app to continue even without database
        }
    }
    
    func selectLanguage(_ language: Language) {
        selectedLanguage = language
        // Don't save language preference - always show selection on app start
        // UserDefaults.standard.set(language.rawValue, forKey: "selectedLanguage")
    }
}