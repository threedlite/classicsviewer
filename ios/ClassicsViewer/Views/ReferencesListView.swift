import SwiftUI

/// Lists the installed reference works. Tapping a row opens PDFReaderView
/// at the entry's last-read page.
struct ReferencesListView: View {
    @StateObject private var manager = ReferencesAssetDownloadManager.shared
    @State private var manifest: ReferencesManifest?
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if let manifest = manifest {
                List(manifest.entries) { entry in
                    NavigationLink {
                        PDFReaderView(entry: entry)
                    } label: {
                        ReferenceRow(entry: entry)
                    }
                }
            } else if let errorMessage = errorMessage {
                Text(errorMessage)
                    .foregroundColor(.secondary)
                    .padding()
            } else {
                ProgressView("Loading…")
            }
        }
        .navigationTitle("References")
        .task {
            await loadManifest()
        }
    }

    private func loadManifest() async {
        await manager.checkStatus()
        if let loaded = await manager.loadManifestIfNeeded() {
            manifest = loaded
        } else {
            errorMessage = "References are not installed."
        }
    }
}

private struct ReferenceRow: View {
    let entry: ReferenceEntry
    @State private var lastPage: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(entry.title)
                .font(.headline)
            Text(entry.author)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text(metaText)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
        .onAppear {
            lastPage = UserDefaults.standard.lastReadPage(entryId: entry.id)
        }
    }

    private var metaText: String {
        if let lastPage = lastPage {
            return "\(entry.pageCount) pages — last read: p. \(lastPage + 1)"
        }
        return "\(entry.pageCount) pages"
    }
}

#if DEBUG
struct ReferencesListView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationStack {
            ReferencesListView()
        }
    }
}
#endif
