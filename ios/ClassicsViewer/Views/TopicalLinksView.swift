import SwiftUI

/// One related-passage row, hydrated from the loaded main DB.
struct TopicalRelatedPassage: Identifiable {
    let id = UUID()
    let reference: String          // "Homer, Iliad  Book 1.15" (English)
    let originalSnippet: String    // limited Greek/Latin
    let translationSnippet: String? // limited aligned English translation
    let kind: String               // "tfidf" or "lda" (used by caller, not rendered per row)
    let workId: String
    let bookId: String
    let bookLabel: String?
    let lineNumber: Int
    let sequenceNumber: Int
    let language: String
    let authorName: String
    let workTitle: String
}

/// Standalone "Topical Links" results screen (iOS). Mirrors Android: a kind
/// dropdown in the header (Topical / Lexical / ...), per-language sticky
/// selection, "No entries found." when empty. Per-row badge removed — the
/// selected kind lives in the header.
struct TopicalLinksView: View {
    let language: String
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int
    let sourceRef: String

    @State private var results: [TopicalRelatedPassage] = []
    @State private var loading = true
    @State private var reader: TopicalReader?
    @State private var kinds: [String] = []
    @State private var kindLabels: [String: String] = [:]
    @State private var selectedKind: String = "lda"

    // Match Android (TopicalLinksActivity). The manifest's defaults
    // (lda_min_sim=0.50, tfidf_min_sim=0.15, ivf_nprobe=10) were calibrated
    // for K=200; at our shipping K=1000 cosines spread lower, so the
    // client is more permissive than the build's conservative default.
    // See TOPICAL.md §4.1.
    private let displayLimit = 50
    private let candidateLimit = 200
    private let ldaMinSimOverride: Float = 0.30
    private let tfidfMinSimOverride: Float = 0.12
    private let entityMinSimOverride: Float = 0.20
    private let ivfNprobeOverride = 24

    var body: some View {
        VStack(spacing: 0) {
            if kinds.count > 1 {
                HStack {
                    Text("Show:").font(.subheadline).foregroundColor(.secondary)
                    Picker("", selection: $selectedKind) {
                        ForEach(kinds, id: \.self) { k in
                            Text(kindLabels[k] ?? k).tag(k)
                        }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: selectedKind) { newValue in
                        UserDefaults.standard.set(
                            newValue, forKey: "topical_selected_kind_\(language.lowercased())"
                        )
                        Task { await runQuery() }
                    }
                    Spacer()
                }
                .padding(.horizontal, 16).padding(.vertical, 8)
                .background(Color.gray.opacity(0.1))
            }
            Group {
                if loading {
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if results.isEmpty {
                    Text("No entries found.")
                        .foregroundColor(.secondary)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(results) { item in
                        NavigationLink(destination: ReaderView(
                            book: Book(id: item.bookId, workId: item.workId, bookNumber: 1,
                                       label: item.bookLabel, startLine: nil, endLine: nil, lineCount: nil),
                            author: Author(id: "", name: item.authorName, nameAlt: nil,
                                           language: item.language, hasTranslations: 0),
                            targetLineNumber: item.lineNumber
                        )) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.reference)
                                    .font(.caption).fontWeight(.bold)
                                    .foregroundColor(.secondary)
                                Text(item.originalSnippet)
                                    .font(.system(size: 17))
                                if let t = item.translationSnippet, !t.isEmpty {
                                    Text(t)
                                        .font(.subheadline).italic()
                                        .foregroundColor(.secondary)
                                }
                            }
                            .padding(.vertical, 2)
                        }
                    }
                    .listStyle(.plain)
                }
            }
        }
        .navigationTitle("Topical Links")
        .navigationBarTitleDisplayMode(.inline)
        .task { await bootstrap() }
    }

    private func bootstrap() async {
        guard let r = await TopicalReader.make(language: language) else {
            loading = false; return
        }
        reader = r
        let ks = await r.kindsAvailable
        kinds = ks.isEmpty ? ["lda"] : ks
        var lbls: [String: String] = [:]
        for k in kinds { lbls[k] = await r.kindUiLabel(k) }
        kindLabels = lbls
        let stickyKey = "topical_selected_kind_\(language.lowercased())"
        let defaultKind = await r.defaultKind
        let sticky = UserDefaults.standard.string(forKey: stickyKey) ?? defaultKind
        selectedKind = kinds.contains(sticky) ? sticky : (kinds.first ?? "lda")
        await runQuery()
    }

    private func runQuery() async {
        guard let r = reader else { return }
        loading = true
        results = []
        let kind = selectedKind
        let srcRow = await r.lookupRow(bookId: bookId, lineNumber: lineNumber,
                                       sequenceNumber: sequenceNumber)
        if srcRow < 0 { loading = false; return }

        let hits: [TopicalReader.Hit]
        switch kind {
        case "lda":
            hits = await r.ldaKnn(srcRowIdx: srcRow, K: candidateLimit,
                                  minSim: ldaMinSimOverride,
                                  nprobe: ivfNprobeOverride)
        case "tfidf":
            let queryTf = await r.sourceBag(rowIdx: srcRow)
            hits = await r.tfidfKnn(srcRowIdx: srcRow, queryTf: queryTf,
                                    K: candidateLimit, minSim: tfidfMinSimOverride)
        case "entity":
            let queryTf = await r.entitySourceBag(rowIdx: srcRow)
            hits = await r.entityKnn(srcRowIdx: srcRow, queryTf: queryTf,
                                     K: candidateLimit, minSim: entityMinSimOverride)
        default:
            hits = []
        }
        if hits.isEmpty { loading = false; return }

        let lineDAO = LineDAO()
        let bookDAO = BookDAO()
        let workDAO = WorkDAO()
        let authorDAO = AuthorDAO()
        let translationDAO = TranslationDAO()

        var out: [TopicalRelatedPassage] = []
        for hit in hits {
            if out.count >= displayLimit { break }
            guard let h = await r.hydrate(hit, kind: kind) else { continue }
            do {
                let lines = try await lineDAO.getLines(bookId: h.bookId,
                                                       startLine: h.lineNumber,
                                                       endLine: h.lineNumber)
                guard let line = lines.first(where: { $0.sequenceNumber == h.sequenceNumber })
                    ?? lines.first else { continue }
                guard let book = try await bookDAO.getBook(bookId: h.bookId) else { continue }
                let work = try await workDAO.getWork(workId: book.workId)
                let author = try await authorDAO.getAuthorWithWorks(
                    authorId: work?.authorId ?? "")?.author
                let workName = (work?.titleEnglish?.isEmpty == false ? work?.titleEnglish : nil)
                    ?? work?.title ?? ""
                let authorName = author?.name ?? ""
                // Drop the interlinear translator's rows — that's per-token
                // lemma+POS text, not human-readable English. Prefix-match
                // so legacy Latin "...AI-generated from app dictionary"
                // rows in unrebuilt on-device DBs are still excluded.
                let translation = (try? await translationDAO.getTranslations(
                    bookId: h.bookId, startLine: h.lineNumber, endLine: h.lineNumber)
                )?.first(where: { !LemmaBagBuilder.isInterlinearTranslator($0.translator) })?.translationText
                out.append(TopicalRelatedPassage(
                    reference: buildReference(authorName, workName, book.label, h.lineNumber),
                    originalSnippet: String(line.lineText.prefix(160)),
                    translationSnippet: translation.map { String($0.prefix(220)) },
                    kind: h.kind,
                    workId: book.workId, bookId: h.bookId, bookLabel: book.label,
                    lineNumber: h.lineNumber, sequenceNumber: h.sequenceNumber,
                    language: language, authorName: authorName, workTitle: workName))
            } catch {
                continue
            }
        }
        results = out
        loading = false
    }

    private func buildReference(_ author: String, _ work: String,
                                _ label: String?, _ line: Int) -> String {
        let head = [author, work].filter { !$0.isEmpty }.joined(separator: ", ")
        let loc = (label?.isEmpty == false) ? "\(label!).\(line)" : "\(line)"
        return head.isEmpty ? loc : "\(head)  \(loc)"
    }
}
