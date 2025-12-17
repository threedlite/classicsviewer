import SwiftUI

/// View for downloading and managing the full database asset pack
struct FullDatabaseDownloadView: View {
    @StateObject private var manager = DatabaseAssetDownloadManager.shared
    @Environment(\.dismiss) private var dismiss
    @AppStorage("colorScheme") private var colorScheme: String = "System"

    @State private var showRestartAlert = false
    @State private var showRevertAlert = false
    @State private var showDeleteAlert = false

    private let assetInfo = AssetPackInfo.databaseFull

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Current database info
                    currentDatabaseSection

                    Divider()

                    // Download/install section
                    statusContent
                }
                .padding()
            }
            .navigationTitle("Full Database")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") { dismiss() }
                }
            }
            .background(backgroundColor)
            .alert("Restart Required", isPresented: $showRestartAlert) {
                Button("Restart Now") {
                    restartApp()
                }
                Button("Later", role: .cancel) {}
            } message: {
                Text("The app needs to restart to use the new database.")
            }
            .alert("Revert to Sample Database?", isPresented: $showRevertAlert) {
                Button("Revert", role: .destructive) {
                    Task {
                        try? await manager.revertToSampleDatabase()
                        showRestartAlert = true
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will switch back to the sample database. The full database will remain downloaded.")
            }
            .alert("Delete Full Database?", isPresented: $showDeleteAlert) {
                Button("Delete", role: .destructive) {
                    Task {
                        await manager.removeFullDatabase()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will permanently delete the downloaded full database and free up storage space.")
            }
        }
        .task {
            await manager.checkStatus()
        }
    }

    // MARK: - Current Database Section

    private var currentDatabaseSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Current Database")
                .font(.headline)

            HStack {
                Image(systemName: manager.currentDatabaseType.iconName)
                    .foregroundColor(databaseColor)
                Text(manager.currentDatabaseType.displayName)
                Spacer()
                if manager.currentDatabaseType == .full {
                    Text("Active")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.green.opacity(0.2))
                        .cornerRadius(4)
                }
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(8)

            Text(manager.currentDatabaseType.description)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Status Content

    @ViewBuilder
    private var statusContent: some View {
        switch manager.status {
        case .unknown:
            loadingSection
        case .notDownloaded:
            downloadSection
        case .downloading:
            downloadingSection
        case .downloaded:
            extractSection
        case .extracting:
            extractingSection
        case .installed:
            installedSection
        case .active:
            activeSection
        case .failed:
            failedSection
        }
    }

    // MARK: - Download Section

    private var downloadSection: some View {
        VStack(spacing: 16) {
            // Size info
            VStack(spacing: 8) {
                InfoRow(label: "Download Size", value: StorageManager.formatBytes(assetInfo.compressedSize))
                InfoRow(label: "Space Required", value: StorageManager.formatBytes(assetInfo.requiredFreeSpace))
                InfoRow(label: "Available Space", value: StorageManager.formatBytes(StorageManager.availableFreeSpace()))
            }
            .padding()
            .background(Color(.secondarySystemBackground))
            .cornerRadius(8)

            if !StorageManager.hasEnoughSpace(for: assetInfo) {
                Label("Not enough storage space", systemImage: "exclamationmark.triangle.fill")
                    .foregroundColor(.red)
            }

            Label("WiFi recommended for large download", systemImage: "wifi")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(action: { Task { await manager.startDownload() } }) {
                Label("Download Full Database", systemImage: "arrow.down.circle.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!StorageManager.hasEnoughSpace(for: assetInfo))
        }
    }

    // MARK: - Downloading

    private var downloadingSection: some View {
        VStack(spacing: 16) {
            ProgressView(value: manager.downloadProgress) {
                Text("Downloading...")
            } currentValueLabel: {
                Text("\(Int(manager.downloadProgress * 100))%")
            }

            Text("This may take several minutes")
                .font(.caption)
                .foregroundColor(.secondary)

            Button("Cancel") {
                manager.cancelDownload()
            }
            .buttonStyle(.bordered)
        }
    }

    // MARK: - Extract Section

    private var extractSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.largeTitle)
                .foregroundColor(.green)

            Text("Download Complete")
                .font(.headline)

            Text("Extract the database to prepare it for use.")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(action: {
                Task {
                    try? await manager.extractDatabase()
                }
            }) {
                Label("Extract Database", systemImage: "archivebox")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Extracting

    private var extractingSection: some View {
        VStack(spacing: 16) {
            ProgressView(value: manager.extractionProgress) {
                Text("Extracting...")
            } currentValueLabel: {
                Text("\(Int(manager.extractionProgress * 100))%")
            }

            Text("This may take several minutes")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Installed (Ready to Activate)

    private var installedSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 50))
                .foregroundColor(.green)

            Text("Full Database Ready")
                .font(.headline)

            Text("Switch to the full database to access all authors and works.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: {
                Task {
                    try? await manager.activateFullDatabase()
                    showRestartAlert = true
                }
            }) {
                Label("Activate Full Database", systemImage: "arrow.right.circle.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)

            Button(role: .destructive, action: { showDeleteAlert = true }) {
                Label("Delete Full Database", systemImage: "trash")
            }
            .buttonStyle(.bordered)
        }
    }

    // MARK: - Active

    private var activeSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 60))
                .foregroundColor(.green)

            Text("Full Database Active")
                .font(.headline)

            Text("You have access to all 100+ Greek and Latin authors.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: { showRevertAlert = true }) {
                Label("Switch to Sample Database", systemImage: "arrow.uturn.backward")
            }
            .buttonStyle(.bordered)
        }
    }

    // MARK: - Failed

    private var failedSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 50))
                .foregroundColor(.red)

            Text("Download Failed")
                .font(.headline)

            if let errorMessage = manager.errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }

            Button(action: { Task { await manager.startDownload() } }) {
                Label("Try Again", systemImage: "arrow.clockwise")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Loading

    private var loadingSection: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Checking status...")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Helpers

    private var backgroundColor: Color {
        colorScheme == "Inverted" ? .white : Color(.systemBackground)
    }

    private var databaseColor: Color {
        switch manager.currentDatabaseType {
        case .sample: return .blue
        case .full: return .green
        case .external: return .orange
        }
    }

    private func restartApp() {
        // Use the app restarter utility
        restartApplication()
    }
}

// MARK: - Preview
// Note: FeatureRow is defined in SettingsView.swift

#Preview {
    FullDatabaseDownloadView()
}
