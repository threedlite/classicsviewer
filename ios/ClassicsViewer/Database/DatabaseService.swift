import Foundation
import SwiftUI

/// App-wide database state management service
@MainActor
class DatabaseService: ObservableObject {
    @Published var isReady = false
    @Published var error: Error?
    @Published var isInitializing = false
    
    init() {}
    
    /// Initialize database connection once at app startup
    func initialize() async {
        guard !isInitializing && !isReady else { return }
        
        isInitializing = true
        error = nil
        
        do {
            print("DatabaseService: Starting database initialization...")
            try await DatabaseManagerAsync.shared.initialize()
            isReady = true
            error = nil
            print("DatabaseService: Database ready")
        } catch {
            print("DatabaseService: Database initialization failed: \(error)")
            self.error = error
            isReady = false
        }
        
        isInitializing = false
    }
    
    /// Retry database initialization after error
    func retry() async {
        print("DatabaseService: Retrying database initialization...")
        error = nil
        isReady = false
        await initialize()
    }
    
    /// Recover from error state
    func recover() async {
        do {
            print("DatabaseService: Attempting recovery...")
            try await DatabaseManagerAsync.shared.recover()
            error = nil
            isReady = true
        } catch {
            print("DatabaseService: Recovery failed: \(error)")
            self.error = error
            isReady = false
        }
    }
    
    /// Get current database status
    func getStatus() async -> String {
        await DatabaseManagerAsync.shared.getStatus()
    }
}
