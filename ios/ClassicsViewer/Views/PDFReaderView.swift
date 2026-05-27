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
    @State private var sliderDragging: Bool = false
    @State private var sliderDragPage: Int = 1

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
                .overlay(alignment: .trailing) {
                    if pageCount > 1 {
                        VerticalPageSlider(
                            pageCount: pageCount,
                            currentPage: currentPageNumber,
                            onDragStateChanged: { dragging in sliderDragging = dragging },
                            onDragProgress: { page in sliderDragPage = page },
                            onPageSelected: { page in jumpTo(page: page) }
                        )
                        .frame(width: 56)
                        .padding(.trailing, 4)
                    }
                }
                .overlay(alignment: .center) {
                    if sliderDragging {
                        Text("Page \(sliderDragPage) / \(pageCount)")
                            .font(.title2.weight(.semibold))
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(Color.black.opacity(0.75))
                            .foregroundColor(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
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
        jumpTo(page: typed)
    }

    private func jumpTo(page: Int) {
        guard page >= 1, page <= pageCount else { return }
        guard let pdfView = pdfViewRef, let target = pdfDocument?.page(at: page - 1) else { return }
        pdfView.go(to: target)
        currentPageNumber = page
    }
}

/// Vertical slider for rapidly navigating to any page in a PDF.
/// Mirrors Android's `VerticalPageSlider`: drag the thumb on the right edge,
/// `onDragProgress(page)` fires continuously while dragging (1-indexed),
/// `onPageSelected(page)` fires once on release so the host can jump.
private struct VerticalPageSlider: View {
    let pageCount: Int
    let currentPage: Int
    let onDragStateChanged: (Bool) -> Void
    let onDragProgress: (Int) -> Void
    let onPageSelected: (Int) -> Void

    @State private var isDragging: Bool = false
    @State private var dragPage: Int = 1

    var body: some View {
        GeometryReader { geo in
            let height = geo.size.height
            let padding: CGFloat = 16
            let usable = max(height - 2 * padding, 1)
            let displayedPage = isDragging ? dragPage : currentPage
            let frac: CGFloat = pageCount > 1
                ? CGFloat(displayedPage - 1) / CGFloat(pageCount - 1)
                : 0
            let thumbCenterY = padding + frac * usable
            let thumbWidth: CGFloat = isDragging ? 40 : 28
            let thumbHeight: CGFloat = isDragging ? 36 : 24

            ZStack(alignment: .top) {
                Capsule()
                    .fill(Color.white.opacity(0.45))
                    .frame(width: 6, height: usable)
                    .offset(y: padding)

                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.white)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.black.opacity(0.8), lineWidth: 2)
                    )
                    .frame(width: thumbWidth, height: thumbHeight)
                    .offset(y: thumbCenterY - thumbHeight / 2)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { value in
                        if !isDragging {
                            isDragging = true
                            onDragStateChanged(true)
                        }
                        updatePage(fromY: value.location.y, usable: usable, padding: padding)
                    }
                    .onEnded { _ in
                        let target = dragPage
                        isDragging = false
                        onDragStateChanged(false)
                        onPageSelected(target)
                    }
            )
        }
    }

    private func updatePage(fromY y: CGFloat, usable: CGFloat, padding: CGFloat) {
        let f = max(0, min(1, (y - padding) / usable))
        let target = Int((f * CGFloat(pageCount - 1)).rounded()) + 1
        let clamped = max(1, min(pageCount, target))
        if clamped != dragPage {
            dragPage = clamped
            onDragProgress(clamped)
        }
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
        // Use absolute scale bounds; `scaleFactorForSizeToFit` is unreliable
        // before the view has been laid out, so deriving min/max from it
        // here can leave the current scale outside the [min,max] range and
        // block pinch-to-zoom. Absolute bounds let PDFKit's built-in pinch
        // gesture work immediately.
        view.minScaleFactor = 0.25
        view.maxScaleFactor = 6.0

        // Restore last-read page + zoom + scroll offset.
        if let saved = UserDefaults.standard.referenceState(entryId: entryId),
           let page = document.page(at: max(0, min(saved.page, document.pageCount - 1))) {
            view.go(to: page)
            if saved.zoom > 0 {
                view.scaleFactor = saved.zoom * view.scaleFactorForSizeToFit
            }
            // Defer scroll-offset restore until layout settles.
            DispatchQueue.main.async {
                if let scrollView = view.documentView as? UIScrollView {
                    scrollView.setContentOffset(
                        CGPoint(x: saved.scrollX, y: saved.scrollY),
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
