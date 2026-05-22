import SwiftUI
import PDFKit

/// Single-PDF reader for the References pack.
///
/// PDFKit handles pinch-to-zoom, double-tap zoom, and page navigation out of
/// the box. We add:
///  - "Go to page" toolbar item
///  - Per-entry persistence (page + zoom + scroll offset) via UserDefaults
///    keys that match Android `PreferencesManager.ReferenceState`.
struct PDFReaderView: View {
    let entry: ReferenceEntry

    @State private var pdfDocument: PDFDocument?
    @State private var currentPageNumber: Int = 1
    @State private var pageCount: Int = 0
    @State private var showGotoPage: Bool = false
    @State private var gotoPageText: String = ""
    @State private var pdfViewRef: PDFView?

    var body: some View {
        Group {
            if let document = pdfDocument {
                PDFKitWrapper(
                    document: document,
                    entryId: entry.id,
                    onPageChange: { page in currentPageNumber = page },
                    pdfViewRef: $pdfViewRef
                )
                .ignoresSafeArea(edges: .bottom)
                .overlay(alignment: .bottom) {
                    Text("Page \(currentPageNumber) / \(pageCount)")
                        .font(.footnote)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color.black.opacity(0.6))
                        .foregroundColor(.white)
                        .clipShape(Capsule())
                        .padding(.bottom, 12)
                }
            } else {
                ProgressView("Loading PDF…")
            }
        }
        .navigationTitle(entry.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    gotoPageText = String(currentPageNumber)
                    showGotoPage = true
                } label: {
                    Image(systemName: "list.number")
                }
                .disabled(pdfDocument == nil)
            }
        }
        .alert("Go to page", isPresented: $showGotoPage) {
            TextField("1 – \(pageCount)", text: $gotoPageText)
                .keyboardType(.numberPad)
            Button("Go", action: jumpToTypedPage)
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Enter a page from 1 to \(pageCount)")
        }
        .task {
            await loadDocument()
        }
    }

    private func loadDocument() async {
        guard let url = await ReferencesAssetDownloadManager.shared.pdfURL(for: entry) else {
            return
        }
        let doc = PDFDocument(url: url)
        await MainActor.run {
            pdfDocument = doc
            pageCount = doc?.pageCount ?? entry.pageCount
            let saved = UserDefaults.standard.referenceState(entryId: entry.id)
            currentPageNumber = (saved?.page ?? 0) + 1
        }
    }

    private func jumpToTypedPage() {
        guard let typed = Int(gotoPageText), typed >= 1, typed <= pageCount else { return }
        guard let pdfView = pdfViewRef, let page = pdfDocument?.page(at: typed - 1) else { return }
        pdfView.go(to: page)
        currentPageNumber = typed
    }
}

/// UIViewRepresentable bridge to PDFKit's PDFView, with hooks for page changes
/// and reading-state persistence.
private struct PDFKitWrapper: UIViewRepresentable {
    let document: PDFDocument
    let entryId: String
    let onPageChange: (Int) -> Void
    @Binding var pdfViewRef: PDFView?

    func makeUIView(context: Context) -> PDFView {
        let view = PDFView()
        view.document = document
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.displayDirection = .vertical
        view.usePageViewController(false)
        view.minScaleFactor = view.scaleFactorForSizeToFit
        view.maxScaleFactor = view.scaleFactorForSizeToFit * 6

        // Restore last-read page + zoom + scroll offset.
        if let saved = UserDefaults.standard.referenceState(entryId: entryId),
           let page = document.page(at: max(0, min(saved.page, document.pageCount - 1))) {
            view.go(to: page)
            if saved.zoom > 0 {
                view.scaleFactor = saved.zoom * view.scaleFactorForSizeToFit
            }
            // Defer scroll-offset restore until layout settles.
            DispatchQueue.main.async {
                if let docView = view.documentView {
                    let target = CGPoint(x: saved.scrollX, y: saved.scrollY)
                    docView.scrollRectToVisible(
                        CGRect(origin: target, size: view.bounds.size),
                        animated: false
                    )
                }
            }
        }

        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.pageChanged(_:)),
            name: .PDFViewPageChanged,
            object: view
        )
        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.persistState(_:)),
            name: UIApplication.willResignActiveNotification,
            object: nil
        )

        context.coordinator.parent = self
        context.coordinator.pdfView = view

        DispatchQueue.main.async {
            self.pdfViewRef = view
        }
        return view
    }

    func updateUIView(_ uiView: PDFView, context: Context) {
        if uiView.document !== document {
            uiView.document = document
        }
    }

    static func dismantleUIView(_ uiView: PDFView, coordinator: Coordinator) {
        coordinator.persistNow()
        NotificationCenter.default.removeObserver(coordinator)
    }

    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    final class Coordinator: NSObject {
        var parent: PDFKitWrapper
        weak var pdfView: PDFView?

        init(parent: PDFKitWrapper) {
            self.parent = parent
        }

        @objc func pageChanged(_ notification: Notification) {
            guard let pdfView = notification.object as? PDFView,
                  let page = pdfView.currentPage,
                  let index = pdfView.document?.index(for: page) else { return }
            parent.onPageChange(index + 1)
            persistNow()
        }

        @objc func persistState(_ notification: Notification) {
            persistNow()
        }

        func persistNow() {
            guard let pdfView = pdfView,
                  let page = pdfView.currentPage,
                  let index = pdfView.document?.index(for: page) else { return }
            let scroll = pdfView.documentView?.bounds.origin ?? .zero
            let fit = max(pdfView.scaleFactorForSizeToFit, 0.001)
            let normalizedZoom = pdfView.scaleFactor / fit
            UserDefaults.standard.setReferenceState(
                entryId: parent.entryId,
                state: ReferenceReadingState(
                    page: index,
                    zoom: normalizedZoom,
                    scrollX: scroll.x,
                    scrollY: scroll.y
                )
            )
        }
    }
}
