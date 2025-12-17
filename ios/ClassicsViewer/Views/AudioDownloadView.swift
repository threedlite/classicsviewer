import SwiftUI

/// View for downloading and managing the full audio asset pack
struct AudioDownloadView: View {
    @StateObject private var manager = AudioAssetDownloadManager.shared
    @Environment(\.dismiss) private var dismiss
    @AppStorage("colorScheme") private var colorScheme: String = "System"

    private let assetInfo = AssetPackInfo.audioFull

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Header with icon
                    audioHeaderSection

                    Divider()

                    // Status-dependent content
                    statusContent
                }
                .padding()
            }
            .navigationTitle("Full Audio")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Close") { dismiss() }
                }
            }
            .background(backgroundColor)
        }
        .task {
            await manager.checkStatus()
        }
    }

    // MARK: - Header Section

    private var audioHeaderSection: some View {
        VStack(spacing: 12) {
            Image(systemName: "waveform.circle.fill")
                .font(.system(size: 60))
                .foregroundColor(.blue)

            Text(assetInfo.displayName)
                .font(.headline)

            Text(assetInfo.description)
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
    }

    // MARK: - Status Content

    @ViewBuilder
    private var statusContent: some View {
        switch manager.status {
        case .unknown:
            loadingSection
        case .notDownloaded:
            notDownloadedSection
        case .downloading:
            downloadingSection
        case .downloaded:
            extractSection
        case .extracting:
            extractingSection
        case .installed:
            installedSection
        case .failed:
            failedSection
        case .active:
            installedSection
        }
    }

    // MARK: - Not Downloaded

    private var notDownloadedSection: some View {
        VStack(spacing: 16) {
            // Size and space info
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

            // WiFi recommendation
            Label("WiFi recommended for large download", systemImage: "wifi")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(action: { Task { await manager.startDownload() } }) {
                Label("Download Audio", systemImage: "arrow.down.circle.fill")
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

    // MARK: - Downloaded (Ready to Extract)

    private var extractSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.largeTitle)
                .foregroundColor(.green)

            Text("Download Complete")
                .font(.headline)

            Text("Extract audio files to use them in the app.")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(action: {
                Task {
                    try? await manager.extractAudio()
                }
            }) {
                Label("Extract Audio", systemImage: "archivebox")
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

            Text("This may take a few minutes")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - Installed

    private var installedSection: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 60))
                .foregroundColor(.green)

            Text("Audio Installed")
                .font(.headline)

            Text("Full Homer Iliad audio is ready to use.")
                .font(.caption)
                .foregroundColor(.secondary)

            Button(role: .destructive, action: {
                Task { await manager.removeAudio() }
            }) {
                Label("Remove Audio", systemImage: "trash")
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
}

// MARK: - Info Row Component

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}

// MARK: - Preview

#Preview {
    AudioDownloadView()
}
