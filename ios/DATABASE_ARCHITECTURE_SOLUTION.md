# iOS Database Architecture Solution

## Executive Summary

The iOS ClassicsViewer app is experiencing crashes and freezes due to improper database access patterns. Multiple views are independently opening and closing the SQLite database connection, causing race conditions, deadlocks, and thread blocking. This document outlines a comprehensive solution to establish a safe, efficient database access architecture.

## Current Problems

### 1. Race Conditions
- Multiple views call `openDatabase()` and `closeDatabase()` simultaneously
- Views compete for database access during navigation
- No coordination between different parts of the app

### 2. Thread Blocking
- All database operations use `DispatchQueue.sync`
- Main thread blocks waiting for database operations
- UI freezes when database operations take time

### 3. Connection Management Issues
- Database opened and closed repeatedly (100+ times during normal usage)
- Each view manages its own database lifecycle
- No connection reuse or pooling

### 4. Deadlock Scenarios
Example deadlock sequence:
1. SearchView opens database on main thread (sync)
2. User navigates to OccurrenceDetailView
3. OccurrenceDetailView tries to open database (sync)
4. Previous view still closing database (sync)
5. Main thread deadlocked waiting for queue

### 5. Error Handling
- No recovery mechanism for database errors
- Crashes cascade through the app
- No graceful degradation

## Proposed Architecture

### Core Principles

1. **Single Connection**: One database connection for the entire app lifecycle
2. **Async Operations**: Never block the main thread
3. **Centralized Management**: Database lifecycle managed in one place
4. **Error Recovery**: Graceful handling and recovery from errors
5. **Thread Safety**: Serial queue with async dispatch

### Architecture Components

```
┌─────────────────────────────────────────────┐
│            ClassicsViewerApp                │
│         (Initialize on launch)              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│           DatabaseService                   │
│    (Observable, manages app-wide state)     │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          DatabaseManager                    │
│   (Singleton, async operations only)        │
│   • Single connection                       │
│   • Serial queue                           │
│   • Async/await interface                  │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│              DAO Layer                      │
│   (WordDAO, LemmaDAO, BookmarkDAO, etc.)   │
│   • No open/close calls                    │
│   • Pure async operations                  │
└─────────────────────────────────────────────┘
```

## Implementation Details

### 1. DatabaseManager Refactor

```swift
// DatabaseManager.swift
import Foundation
import SQLite3

actor DatabaseManager {
    static let shared = DatabaseManager()

    private var db: OpaquePointer?
    private var state: ConnectionState = .uninitialized

    private enum ConnectionState {
        case uninitialized
        case initializing
        case ready
        case error(Error)
    }

    // Initialize once at app startup
    func initialize() async throws {
        guard state == .uninitialized else {
            if case .error(let error) = state {
                throw error
            }
            return
        }

        state = .initializing

        do {
            try await openDatabaseConnection()
            state = .ready
        } catch {
            state = .error(error)
            throw error
        }
    }

    // Async query execution
    func executeQuery<T>(
        _ query: String,
        parameters: [Any?] = [],
        mapper: @escaping (OpaquePointer) -> T?
    ) async throws -> [T] {
        try await ensureReady()

        return try await withCheckedThrowingContinuation { continuation in
            Task {
                do {
                    let results = try performQuery(query, parameters: parameters, mapper: mapper)
                    continuation.resume(returning: results)
                } catch {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private func ensureReady() async throws {
        switch state {
        case .ready:
            return
        case .uninitialized:
            try await initialize()
        case .initializing:
            // Wait for initialization to complete
            while state == .initializing {
                try await Task.sleep(nanoseconds: 10_000_000) // 10ms
            }
            try await ensureReady()
        case .error(let error):
            throw error
        }
    }
}
```

### 2. App Lifecycle Integration

```swift
// ClassicsViewerApp.swift
@main
struct ClassicsViewerApp: App {
    @StateObject private var databaseService = DatabaseService()

    var body: some Scene {
        WindowGroup {
            if databaseService.isReady {
                ContentView()
                    .environmentObject(databaseService)
            } else if let error = databaseService.error {
                DatabaseErrorView(error: error) {
                    Task {
                        await databaseService.retry()
                    }
                }
            } else {
                LaunchScreen()
                    .task {
                        await databaseService.initialize()
                    }
            }
        }
    }
}

// DatabaseService.swift
@MainActor
class DatabaseService: ObservableObject {
    @Published var isReady = false
    @Published var error: Error?

    func initialize() async {
        do {
            try await DatabaseManager.shared.initialize()
            isReady = true
            error = nil
        } catch {
            self.error = error
            isReady = false
        }
    }

    func retry() async {
        error = nil
        await initialize()
    }
}
```

### 3. DAO Layer Updates

```swift
// WordDAO.swift - Updated pattern
class WordDAO {
    // No more database lifecycle management
    func searchWords(
        query: String,
        bookId: String?,
        normalized: Bool
    ) async throws -> [WordOccurrence] {
        let queryString = """
            SELECT ... FROM words WHERE ...
        """

        // Direct async call - no open/close
        return try await DatabaseManager.shared.executeQuery(
            queryString,
            parameters: [query, bookId],
            mapper: wordOccurrenceFromStatement
        )
    }
}
```

### 4. View Layer Updates

```swift
// SearchView.swift - Updated pattern
@MainActor
class SearchViewModel: ObservableObject {
    @Published var results: [WordOccurrence] = []
    @Published var isLoading = false
    @Published var error: Error?

    private let wordDAO = WordDAO()

    func search(query: String) async {
        isLoading = true
        error = nil

        do {
            // Simple async call - no database management
            results = try await wordDAO.searchWords(
                query: query,
                bookId: nil,
                normalized: false
            )
        } catch {
            self.error = error
        }

        isLoading = false
    }
}
```

## Migration Plan

### Phase 1: Core Infrastructure (Week 1)
1. Create new `DatabaseManager` with actor-based async implementation
2. Add `DatabaseService` for app-wide state management
3. Update app initialization to open database once

### Phase 2: DAO Migration (Week 2)
1. Update all DAO classes to use async/await
2. Remove all `openDatabase`/`closeDatabase` calls
3. Update method signatures to be async

### Phase 3: View Updates (Week 3)
1. Remove database lifecycle management from all views
2. Update ViewModels to use async DAO methods
3. Add proper error handling UI

### Phase 4: Testing & Refinement (Week 4)
1. Stress test navigation scenarios
2. Test error recovery mechanisms
3. Performance optimization

## Benefits

### Immediate Benefits
- **No more freezes**: Async operations don't block the main thread
- **No more crashes**: Proper error handling and recovery
- **Faster performance**: No overhead from repeated open/close

### Long-term Benefits
- **Maintainability**: Centralized database management
- **Scalability**: Easy to add new features without database concerns
- **Testability**: Mockable async interfaces

## Risk Mitigation

### Potential Risks
1. **Migration bugs**: Extensive testing during each phase
2. **Performance regression**: Benchmark before and after
3. **Data corruption**: Implement transaction support

### Rollback Strategy
- Keep old implementation behind feature flag
- Gradual rollout to beta testers
- Monitor crash reports closely

## Success Metrics

1. **Crash Rate**: Reduce database-related crashes to zero
2. **UI Responsiveness**: No freezes longer than 100ms
3. **Performance**: Database operations < 50ms for common queries
4. **User Satisfaction**: Improved app store ratings

## Code Examples

### Before (Current Problem)
```swift
// This pattern appears 50+ times in the codebase
func loadData() async {
    do {
        try DatabaseManager.shared.openDatabase()  // BLOCKS
        let data = try await dao.getData()         // BLOCKS
        DatabaseManager.shared.closeDatabase()     // BLOCKS
    } catch {
        // Handle error
    }
}
```

### After (Solution)
```swift
// Clean, simple, non-blocking
func loadData() async {
    do {
        let data = try await dao.getData()  // Async, non-blocking
    } catch {
        // Handle error
    }
}
```

## Testing Strategy

### Unit Tests
- Mock database responses
- Test error scenarios
- Verify async behavior

### Integration Tests
- Test complete user flows
- Simulate rapid navigation
- Test database recovery

### Stress Tests
- 1000+ rapid operations
- Concurrent access patterns
- Memory leak detection

## Conclusion

This architecture solves the fundamental database access problems in the iOS app by:
1. Eliminating race conditions through single connection management
2. Preventing UI freezes with async operations
3. Improving performance by removing unnecessary overhead
4. Providing robust error handling and recovery

The migration can be done incrementally with minimal risk, and the benefits will be immediately visible to users through improved app stability and responsiveness.

## Appendix: File Changes Required

### Files to Modify
- `DatabaseManager.swift` - Complete rewrite
- `ClassicsViewerApp.swift` - Add initialization
- All DAO files (8 files) - Update to async
- All View files with database access (20+ files) - Remove open/close

### New Files
- `DatabaseService.swift` - App-wide state management
- `DatabaseError.swift` - Comprehensive error types
- `DatabaseConfiguration.swift` - Configuration settings

### Deprecated Patterns
- `DispatchQueue.sync` for database operations
- `openDatabase()`/`closeDatabase()` in views
- Direct SQLite error codes in UI layer

## Implementation Timeline

- **Week 1**: Core infrastructure
- **Week 2**: DAO migration
- **Week 3**: View updates
- **Week 4**: Testing and refinement
- **Week 5**: Beta rollout
- **Week 6**: Production release

Total estimated effort: 6 weeks for complete migration