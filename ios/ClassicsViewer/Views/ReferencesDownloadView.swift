import SwiftUI

/// Download UI for the References ODR pack. Mirrors AudioDownloadView /
/// FullDatabaseDownloadView. Shown when the user taps "Download References"
/// from the main menu and the pack is not yet on-device.
struct ReferencesDownloadView: View {
    @StateObject private var manager = ReferencesAssetDownloadManager.shared
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Reference Grammars")
                .font(.title2.bold())

            Text("Smyth's *Greek Grammar for Colleges*, Allen & Greenough's *New Latin Grammar*, and Whitney's *Sanskrit Grammar* are available as an optional download (about 100 MB). They are available offline once installed.")
                .font(.body)

            switch manager.status {
            case .unknown:
                ProgressView("Checking…")
            case .notDownloaded, .failed:
                Button(action: {
                    Task { await manager.startDownload() }
                }) {
                    Label("Download (~100 MB)", systemImage: "arrow.down.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
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
        .navigationTitle("Download References")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await manager.checkStatus()
        }
    }
}

#if DEBUG
struct ReferencesDownloadView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationStack {
            ReferencesDownloadView()
        }
    }
}
#endif
