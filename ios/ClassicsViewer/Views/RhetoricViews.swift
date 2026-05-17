import SwiftUI

/// Render rhetoric text that may carry <i>/<b> emphasis (kept by the importer)
/// and \n\n paragraph breaks, as an AttributedString.
func rhetoricText(_ raw: String?) -> AttributedString {
    guard let raw, !raw.isEmpty else { return AttributedString("") }
    var markdown = raw
        .replacingOccurrences(of: "<i>", with: "*")
        .replacingOccurrences(of: "</i>", with: "*")
        .replacingOccurrences(of: "<b>", with: "**")
        .replacingOccurrences(of: "</b>", with: "**")
    markdown = markdown.replacingOccurrences(
        of: "<[^>]+>", with: "", options: .regularExpression)
    if let attributed = try? AttributedString(
        markdown: markdown,
        options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)) {
        return attributed
    }
    return AttributedString(markdown)
}

// MARK: - Section list (top-level Rhetoric screen)

struct RhetoricSectionListView: View {
    @State private var sections: [RhetoricSection] = []
    @State private var errorMessage: String?
    @State private var showingAbout = false

    var body: some View {
        List {
            if let errorMessage {
                Text(errorMessage).foregroundStyle(.secondary)
            }
            ForEach(sections) { section in
                NavigationLink {
                    RhetoricEntryListView(section: section)
                } label: {
                    HStack {
                        Text(section.title).fontWeight(.medium)
                        Spacer()
                        Text("\(section.entryCount)").foregroundStyle(.secondary)
                    }
                }
            }
        }
        .navigationTitle("Rhetoric (Silva Rhetoricae)")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showingAbout = true
                } label: {
                    Image(systemName: "info.circle")
                }
            }
        }
        .sheet(isPresented: $showingAbout) { RhetoricAboutView() }
        .task {
            do {
                sections = try await RhetoricDatabase.shared.sections()
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}

// MARK: - Entry list for one section

struct RhetoricEntryListView: View {
    let section: RhetoricSection
    @State private var entries: [RhetoricEntryRef] = []
    @State private var errorMessage: String?

    var body: some View {
        List {
            if let errorMessage {
                Text(errorMessage).foregroundStyle(.secondary)
            }
            ForEach(entries) { entry in
                NavigationLink(entry.name) {
                    RhetoricEntryDetailView(entryId: entry.id)
                }
            }
        }
        .navigationTitle(section.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            do {
                entries = try await RhetoricDatabase.shared.entries(sectionId: section.id)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}

// MARK: - Entry detail

struct RhetoricEntryDetailView: View {
    let entryId: String
    @AppStorage("fontSize") private var fontSize: Double = 20

    @State private var entry: RhetoricEntry?
    @State private var related: [RhetoricCrossRef] = []
    @State private var seeAlso: [RhetoricCrossRef] = []
    @State private var errorMessage: String?
    @State private var loaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if let entry {
                    Text(entry.name)
                        .font(.system(size: fontSize * 1.5, weight: .bold))

                    let etymology = etymologyLine(entry)
                    if !etymology.characters.isEmpty {
                        Text(etymology)
                            .font(.system(size: fontSize * 0.9))
                            .italic()
                            .foregroundStyle(.secondary)
                    }

                    Text(rhetoricText(entry.definition))
                        .font(.system(size: fontSize))

                    if let examples = entry.examples, !examples.isEmpty {
                        sectionLabel("Examples")
                        Text(rhetoricText(examples)).font(.system(size: fontSize))
                    }

                    crossRefSection("Related Figures", related)
                    crossRefSection("See Also", seeAlso)
                } else if let errorMessage {
                    Text(errorMessage).foregroundStyle(.secondary)
                } else {
                    ProgressView()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .navigationTitle(entry?.name ?? "")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if loaded { return }
            loaded = true
            await load()
        }
    }

    private func etymologyLine(_ entry: RhetoricEntry) -> AttributedString {
        var pieces: [AttributedString] = []
        if let greek = entry.etymologyGreek, !greek.isEmpty {
            pieces.append(AttributedString(greek))
        }
        if let etymology = entry.etymology, !etymology.isEmpty {
            pieces.append(rhetoricText(etymology))
        }
        var result = AttributedString("")
        for (index, piece) in pieces.enumerated() {
            if index > 0 { result += AttributedString("  ") }
            result += piece
        }
        return result
    }

    @ViewBuilder
    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: fontSize * 1.05, weight: .semibold))
            .padding(.top, 8)
    }

    @ViewBuilder
    private func crossRefSection(_ title: String, _ refs: [RhetoricCrossRef]) -> some View {
        if !refs.isEmpty {
            sectionLabel(title)
            ForEach(refs) { ref in
                NavigationLink {
                    RhetoricEntryDetailView(entryId: ref.toId)
                } label: {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(ref.toName).font(.system(size: fontSize, weight: .medium))
                        if let note = ref.note, !note.isEmpty {
                            Text(rhetoricText(note))
                                .font(.system(size: fontSize * 0.85))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func load() async {
        do {
            // The build guarantees valid cross-reference targets; if an id is
            // somehow unknown, fail soft rather than crash.
            guard let loadedEntry = try await RhetoricDatabase.shared.entry(id: entryId) else {
                errorMessage = "Entry unavailable."
                return
            }
            entry = loadedEntry
            let refs = try await RhetoricDatabase.shared.crossRefs(fromId: entryId)
            related = refs.filter { $0.kind == "related" }
            seeAlso = refs.filter { $0.kind == "see_also" }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Attribution (CC BY 3.0)

struct RhetoricAboutView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                Text("""
                This rhetoric reference is adapted from "Silva Rhetoricae" \
                (rhetoric.byu.edu) by Dr. Gideon O. Burton, Brigham Young University.

                Licensed under Creative Commons Attribution 3.0 (CC BY 3.0):
                https://creativecommons.org/licenses/by/3.0/

                The content was adapted from its original HTML into a structured \
                database for offline use in this app.
                """)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle("About this reference")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
