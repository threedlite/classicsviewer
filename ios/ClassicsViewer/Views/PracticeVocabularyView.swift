import SwiftUI

/// Practice Vocabulary: tap a word, then tap its definition. Same mechanic and
/// scoring as PracticeAlphabetsView; the layout is stacked (word chips above,
/// full-width definition tiles below) because definitions are long, and only
/// the game area scrolls. Mirrors the Android VocabularyGameActivity.
struct PracticeVocabularyView: View {
    @AppStorage("colorScheme") private var colorScheme: SettingsView.ColorScheme = .system

    @State private var currentLanguage = "Greek"
    @State private var wordCount = 3
    @State private var sets: [VocabularySet] = []
    @State private var currentSetLabel = ""
    @State private var points = 0
    @State private var currentRound: [VocabularyEntry] = []
    @State private var shuffledDefinitions: [String] = []
    @State private var matchedHeadwords: Set<String> = []
    @State private var selectedEntry: VocabularyEntry? = nil
    @State private var hasMistake = false
    @State private var isFirstRound = true
    @State private var messageText = ""
    @State private var messageColor = Color.gray
    @State private var hasAchievedMastery = false
    @State private var showMasteryGlow = false
    @State private var flashingDefinition: String? = nil
    @State private var masteredHeadwords: Set<String> = []
    @State private var detailEntry: VocabularyEntry? = nil
    @State private var showingAbout = false
    @State private var showingResetConfirm = false
    /// Identifies the round a delayed "next round" restart belongs to, so a
    /// set, count or language change during the 3-second pause cancels it.
    @State private var roundToken = UUID()

    private var languageKey: String { currentLanguage.lowercased() }

    private var currentSet: VocabularySet? {
        sets.first { $0.label == currentSetLabel }
    }

    private var isInverted: Bool { colorScheme == .inverted }
    private var backgroundColor: Color { isInverted ? .white : .black }
    private var textColor: Color { isInverted ? .black : .white }
    private var secondaryTextColor: Color { isInverted ? Color(white: 0.4) : Color(white: 0.7) }
    private var cardBackgroundColor: Color { isInverted ? Color(white: 0.96) : Color(white: 0.13) }

    var body: some View {
        VStack(spacing: 8) {
            header
            pointsLine
            gameArea
            Text(messageText)
                .font(.subheadline)
                .foregroundColor(messageColor)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, minHeight: 24)
                .padding(4)
        }
        .padding(12)
        .background(backgroundColor)
        .navigationTitle("Practice Vocabulary")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    Button("Reset progress", role: .destructive) { showingResetConfirm = true }
                    Button("About these word lists") { showingAbout = true }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(isPresented: $showingAbout) { VocabularyAboutView() }
        .sheet(item: $detailEntry) { entry in VocabularyEntryDetailView(entry: entry) }
        .confirmationDialog("Reset progress", isPresented: $showingResetConfirm, titleVisibility: .visible) {
            Button("Reset progress", role: .destructive) { resetProgress() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Clear the record of which words you have mastered in this language? Points for this session are also reset.")
        }
        .onAppear {
            if sets.isEmpty {
                loadSets()
                startRound()
            }
        }
    }

    // MARK: - Subviews

    private var header: some View {
        VStack(spacing: 8) {
            HStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Language")
                        .font(.caption)
                        .foregroundColor(secondaryTextColor)
                    Picker("Language", selection: $currentLanguage) {
                        ForEach(VocabularyData.availableLanguages, id: \.self) { Text($0).tag($0) }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: currentLanguage) { resetForNewLanguage() }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                VStack(alignment: .leading, spacing: 2) {
                    Text("Words")
                        .font(.caption)
                        .foregroundColor(secondaryTextColor)
                    Picker("Words", selection: $wordCount) {
                        ForEach(2...7, id: \.self) { Text("\($0)").tag($0) }
                    }
                    .pickerStyle(.menu)
                    .onChange(of: wordCount) { startRound() }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text("Set (by frequency)")
                    .font(.caption)
                    .foregroundColor(secondaryTextColor)
                Picker("Set", selection: $currentSetLabel) {
                    ForEach(sets) { Text($0.label).tag($0.label) }
                }
                .pickerStyle(.menu)
                .onChange(of: currentSetLabel) {
                    hasAchievedMastery = false
                    startRound()
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(12)
        .background(cardBackgroundColor)
        .cornerRadius(12)
    }

    private var pointsLine: some View {
        VStack(spacing: 2) {
            Text(hasAchievedMastery ? "⭐ Points: \(points) ⭐" : "Points: \(points)")
                .font(.headline)
                .fontWeight(.bold)
                .foregroundColor(isInverted ? .white : .black)
                .frame(maxWidth: .infinity)
                .padding(8)
                .background(isInverted ? Color(white: 0.2) : .white)
                .cornerRadius(8)
                .scaleEffect(showMasteryGlow ? 1.1 : 1.0)
                .animation(.easeInOut(duration: 0.3), value: showMasteryGlow)
            Text("Mastered \(masteredInCurrentSet) of \(currentSet?.entries.count ?? 0) in this set")
                .font(.caption)
                .foregroundColor(secondaryTextColor)
        }
    }

    private var gameArea: some View {
        ScrollView {
            VStack(spacing: 4) {
                Text("WORDS")
                    .font(.caption)
                    .foregroundColor(secondaryTextColor)
                    .tracking(1)

                if currentRound.isEmpty {
                    Text("Vocabulary list not available.")
                        .foregroundColor(secondaryTextColor)
                        .padding()
                } else {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 96), spacing: 8)], spacing: 8) {
                        ForEach(currentRound) { entry in
                            VocabularyWordChip(
                                text: entry.lemma,
                                isMatched: matchedHeadwords.contains(entry.headword),
                                isSelected: selectedEntry?.headword == entry.headword
                            )
                            .onTapGesture { handleWordTap(entry) }
                            .onLongPressGesture { detailEntry = entry }
                        }
                    }
                    .padding(.bottom, 8)

                    Text("DEFINITIONS")
                        .font(.caption)
                        .foregroundColor(secondaryTextColor)
                        .tracking(1)

                    ForEach(shuffledDefinitions, id: \.self) { definition in
                        VocabularyDefinitionTile(
                            text: definition,
                            isMatched: isDefinitionMatched(definition),
                            isFlashing: flashingDefinition == definition
                        )
                        .onTapGesture { handleDefinitionTap(definition) }
                    }
                }
            }
            .padding(12)
        }
        .background(cardBackgroundColor)
        .cornerRadius(12)
        .frame(maxHeight: .infinity)
    }

    // MARK: - State

    private var masteredInCurrentSet: Int {
        guard let set = currentSet else { return 0 }
        return set.entries.filter { masteredHeadwords.contains($0.headword) }.count
    }

    private func isDefinitionMatched(_ definition: String) -> Bool {
        currentRound.contains { $0.definition == definition && matchedHeadwords.contains($0.headword) }
    }

    private func loadSets() {
        sets = VocabularyData.sets(for: languageKey)
        currentSetLabel = sets.first?.label ?? ""
        masteredHeadwords = VocabularyProgress.mastered(languageKey)
    }

    private func handleWordTap(_ entry: VocabularyEntry) {
        if matchedHeadwords.contains(entry.headword) { return }
        selectedEntry = entry
        messageText = ""
    }

    private func handleDefinitionTap(_ definition: String) {
        if isDefinitionMatched(definition) { return }

        guard let selected = selectedEntry else {
            messageText = "Select a word first"
            messageColor = .orange
            return
        }

        if selected.definition == definition {
            matchedHeadwords.insert(selected.headword)
            selectedEntry = nil

            if matchedHeadwords.count == currentRound.count {
                let earnedPoints = hasMistake ? 1 : 10
                points += earnedPoints

                if hasMistake {
                    messageText = "Correct! +1 point. Next round in 3 seconds..."
                } else {
                    messageText = "Perfect! +10 points! Next round in 3 seconds..."
                    let headwords = currentRound.map { $0.headword }
                    VocabularyProgress.addMastered(languageKey, headwords)
                    masteredHeadwords.formUnion(headwords)
                    checkForMastery()
                }
                messageColor = .green

                let token = roundToken
                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    if token == roundToken { startRound() }
                }
            }
        } else {
            hasMistake = true
            messageText = "Try again!"
            messageColor = .red
            flashWrong(definition)
        }
    }

    /// Fades the tapped definition tile from red back to normal.
    private func flashWrong(_ definition: String) {
        flashingDefinition = definition
        withAnimation(.easeInOut(duration: 0.6)) {
            flashingDefinition = nil
        }
    }

    private func startRound() {
        roundToken = UUID()
        matchedHeadwords = []
        selectedEntry = nil
        hasMistake = false
        flashingDefinition = nil

        if isFirstRound {
            messageText = "Tap a word, then tap its definition. Long-press a word for details."
            messageColor = .gray
            isFirstRound = false
        } else {
            messageText = ""
        }

        guard let set = currentSet else {
            currentRound = []
            shuffledDefinitions = []
            return
        }
        masteredHeadwords = VocabularyProgress.mastered(languageKey)
        if !hasAchievedMastery && set.entries.allSatisfy({ masteredHeadwords.contains($0.headword) }) {
            hasAchievedMastery = true
        }

        currentRound = pickRound(from: set.entries, mastered: masteredHeadwords, count: wordCount)
        shuffledDefinitions = currentRound.map { $0.definition }.shuffled()
    }

    /// Draws `count` entries from `pool`, unmastered words first. A round never
    /// holds two entries with the same definition text (the tiles would be
    /// indistinguishable) nor two with the same lemma (homographs such as the
    /// Latin adverb and verb both spelled adeō would show identical chips).
    private func pickRound(from pool: [VocabularyEntry], mastered: Set<String>, count: Int) -> [VocabularyEntry] {
        let ordered = pool.filter { !mastered.contains($0.headword) }.shuffled()
            + pool.filter { mastered.contains($0.headword) }.shuffled()
        var result: [VocabularyEntry] = []
        var usedDefinitions = Set<String>()
        var usedLemmas = Set<String>()
        for entry in ordered {
            if !usedDefinitions.contains(entry.definition) && !usedLemmas.contains(entry.lemma) {
                result.append(entry)
                usedDefinitions.insert(entry.definition)
                usedLemmas.insert(entry.lemma)
                if result.count >= count { break }
            }
        }
        return result
    }

    private func resetForNewLanguage() {
        points = 0
        hasAchievedMastery = false
        loadSets()
        startRound()
    }

    private func resetProgress() {
        VocabularyProgress.clear(languageKey)
        masteredHeadwords = []
        hasAchievedMastery = false
        points = 0
        startRound()
    }

    private func checkForMastery() {
        if hasAchievedMastery { return }
        guard let set = currentSet else { return }
        if set.entries.allSatisfy({ masteredHeadwords.contains($0.headword) }) {
            hasAchievedMastery = true
            showMasteryGlow = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                showMasteryGlow = false
            }
        }
    }
}

// MARK: - Tiles

struct VocabularyWordChip: View {
    let text: String
    let isMatched: Bool
    let isSelected: Bool

    var body: some View {
        Text(text)
            .font(.system(size: 24, weight: .medium))
            .foregroundColor(isMatched ? .white : .black)
            .lineLimit(1)
            .minimumScaleFactor(0.6)
            .padding(.horizontal, 10)
            .frame(maxWidth: .infinity, minHeight: 48)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isMatched ? Color.green : (isSelected ? Color.yellow : Color.white))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.orange : Color.clear, lineWidth: 3)
            )
            .shadow(radius: isSelected ? 4 : 2)
    }
}

struct VocabularyDefinitionTile: View {
    let text: String
    let isMatched: Bool
    let isFlashing: Bool

    private var fill: Color {
        if isMatched { return .green }
        if isFlashing { return .red }
        return Color(white: 0.95)
    }

    var body: some View {
        Text(text)
            .font(.system(size: 16))
            .foregroundColor(isMatched ? .white : .black)
            .multilineTextAlignment(.leading)
            .padding(12)
            .frame(maxWidth: .infinity, minHeight: 48, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 8).fill(fill))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.gray.opacity(0.4), style: StrokeStyle(lineWidth: 1, dash: [4, 2]))
            )
    }
}

// MARK: - Entry details

struct VocabularyEntryDetailView: View {
    let entry: VocabularyEntry
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text(entry.headword)
                        .font(.title2)
                    Text(entry.definition)
                        .font(.body)
                    Text(entry.pos)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text(entry.group)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Text("Frequency rank \(entry.rank)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle(entry.lemma)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

// MARK: - Attribution (CC BY-SA 3.0)

struct VocabularyAboutView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                Text("""
                Both word lists are the Core Vocabularies from Dickinson College \
                Commentaries (DCC), ordered by frequency, with definitions shown as published.

                Greek: the DCC Greek Core Vocabulary (dcc.dickinson.edu/greek-core-list), \
                about 500 of the most frequent words in ancient Greek. Compiled in 2012–13 by \
                Christopher Francese with Wilfred Major, Eric Casey, Meghan Reedy, Marc \
                Mastrangelo, Alice Ettling, James Martin, Meredith Wilson and Lara Frymark, \
                from frequency data supplied by the Thesaurus Linguae Graecae and the Perseus \
                Project. Retrieved 2026-09-24.

                Latin: the DCC Latin Core Vocabulary (dcc.dickinson.edu/latin-vocabulary-list), \
                about 1,000 of the most frequent words in Latin. Retrieved 2026-09-26.

                Both lists are licensed under Creative Commons Attribution-ShareAlike 3.0 \
                Unported (CC BY-SA 3.0):
                https://creativecommons.org/licenses/by-sa/3.0/

                The lists are bundled for offline use.
                """)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle("About these word lists")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

#Preview {
    NavigationStack {
        PracticeVocabularyView()
    }
}
