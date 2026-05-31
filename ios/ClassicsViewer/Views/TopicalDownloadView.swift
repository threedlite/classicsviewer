import SwiftUI

/// Download UI for the Topical-links ODR pack. Mirrors ReferencesDownloadView /
/// AudioDownloadView. Shown when the user taps "Topical Links" in Settings →
/// Downloads and the pack is not yet on-device.
struct TopicalDownloadView: View {
    @StateObject private var manager = TopicalAssetDownloadManager.shared
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Topical Links (Beta)")
                .font(.title2.bold())

            Text("Finds passages elsewhere in the corpus related to the one you're reading, for Greek and Latin. Works offline once installed.")
                .font(.body)

            switch manager.status {
            case .unknown:
                ProgressView("Checking…")
            case .notDownloaded, .failed:
                VStack(spacing: 8) {
                    InfoRow(label: "Download Size",
                            value: StorageManager.formatBytes(AssetPackInfo.topical.compressedSize))
                    InfoRow(label: "Space Required",
                            value: StorageManager.formatBytes(AssetPackInfo.topical.requiredFreeSpace))
                    InfoRow(label: "Available Space",
                            value: StorageManager.formatBytes(StorageManager.availableFreeSpace()))
                }
                .padding()
                .background(Color(.secondarySystemBackground))
                .cornerRadius(8)

                if !StorageManager.hasEnoughSpace(for: AssetPackInfo.topical) {
                    Label("Not enough storage space", systemImage: "exclamationmark.triangle.fill")
                        .foregroundColor(.red)
                        .font(.footnote)
                }

                Button(action: {
                    Task { await manager.startDownload() }
                }) {
                    Label("Download (~520 MB, needs ~2 GB free)", systemImage: "arrow.down.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!StorageManager.hasEnoughSpace(for: AssetPackInfo.topical))
                if let msg = manager.errorMessage, manager.status == .failed {
                    Text(msg)
                        .foregroundColor(.red)
                        .font(.footnote)
                }
            case .downloading:
                ProgressView(value: manager.downloadProgress) {
                    Text("Downloading…")
                } currentValueLabel: {
                    Text("\(Int(manager.downloadProgress * 100))%")
                }
                Button("Cancel", role: .cancel) {
                    Task { await manager.cancelDownload() }
                }
            case .downloaded, .extracting:
                ProgressView("Preparing…")
            case .installed, .active:
                VStack(alignment: .leading, spacing: 8) {
                    Label("Installed", systemImage: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Button("Done") { dismiss() }
                        .buttonStyle(.bordered)
                }
            }

            Spacer()
        }
        .padding()
        .navigationTitle("Download Topical Links")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await manager.checkStatus()
        }
    }
}

#if DEBUG
struct TopicalDownloadView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationStack {
            TopicalDownloadView()
        }
    }
}
#endif
