import SwiftUI

/// View for downloading and managing the extended database asset pack
struct ExtendedDatabaseDownloadView: View {
    @StateObject private var manager = ExtendedDatabaseDownloadManager.shared
    @Environment(\.dismiss) private var dismiss
    @AppStorage("colorScheme") private var colorScheme: String = "System"

    @State private var showRestartAlert = false
    @State private var showRevertAlert = false
    @State private var showDeleteAlert = false

    private let assetInfo = AssetPackInfo.databaseExtended

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
            .navigationTitle("Extended Database")
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
                Text("This will switch back to the sample database. The extended database will remain downloaded.")
            }
            .alert("Delete Extended Database?", isPresented: $showDeleteAlert) {
                Button("Delete", role: .destructive) {
                    Task {
                        await manager.removeExtendedDatabase()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will permanently delete the downloaded extended database and free up storage space.")
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
                if manager.currentDatabaseType == .extended {
                    Text("Active")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.purple.opacity(0.2))
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
            // Description
            VStack(alignment: .leading, spacing: 8) {
                Text("Extended Database")
                    .font(.headline)
                Text("Includes Perseus + First1KGreek + PTA (~2,600 works). This is the most comprehensive collection of Greek and Latin texts available.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .background(Color.purple.opacity(0.1))
            .cornerRadius(8)

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

            Label("WiFi recommended for large download (~3.5 GB)", systemImage: "wifi")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(action: { Task { await manager.startDownload() } }) {
                Label("Download Extended Database", systemImage: "arrow.down.circle.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.purple)
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
            .tint(.purple)

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
                .foregroundColor(.purple)

            Text("Download Complete")
                .font(.headline)

            Text("Extract the database to prepare it for use. This requires ~17 GB of free space.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: {
                Task {
                    try? await manager.extractDatabase()
                }
            }) {
                Label("Extract Database", systemImage: "archivebox")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.purple)
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
            .tint(.purple)

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
                .foregroundColor(.purple)

            Text("Extended Database Ready")
                .font(.headline)

            Text("Switch to the extended database to access ~2,600 works from Perseus, First1KGreek, and PTA.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: {
                Task {
                    try? await manager.activateExtendedDatabase()
                    showRestartAlert = true
                }
            }) {
                Label("Activate Extended Database", systemImage: "arrow.right.circle.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.purple)

            Button(role: .destructive, action: { showDeleteAlert = true }) {
                Label("Delete Extended Database", systemImage: "trash")
            }
            .buttonStyle(.bordered)
        }
    }

    // MARK: - Active

    private var activeSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 60))
                .foregroundColor(.purple)

            Text("Extended Database Active")
                .font(.headline)

            Text("You have access to ~2,600 works from Perseus, First1KGreek, and PTA.")
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
            .tint(.purple)
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
        case .extended: return .purple
        case .external: return .orange
        }
    }

    private func restartApp() {
        restartApplication()
    }
}

// MARK: - Preview

#Preview {
    ExtendedDatabaseDownloadView()
}
