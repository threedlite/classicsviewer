import SwiftUI

struct PracticeAlphabetsView: View {
    @AppStorage("colorScheme") private var colorScheme: SettingsView.ColorScheme = .system

    @State private var currentLanguage = "Greek"
    @State private var letterCount = 3
    @State private var includeCombinedForms = false
    @State private var points = 0
    @State private var currentRound: [AlphabetLetter] = []
    @State private var shuffledPhonetics: [String] = []
    @State private var matchedLetters: Set<String> = []
    @State private var selectedLetter: AlphabetLetter? = nil
    @State private var hasMistake = false
    @State private var isFirstRound = true
    @State private var messageText = ""
    @State private var messageColor = Color.gray
    @State private var showNextRoundTimer = false

    // Mastery tracking
    @State private var masteredLetters: Set<String> = []
    @State private var perfectStreak = true
    @State private var hasAchievedMastery = false
    @State private var showMasteryGlow = false

    private var isInverted: Bool {
        colorScheme == .inverted
    }

    private var backgroundColor: Color {
        isInverted ? .white : .black
    }

    private var textColor: Color {
        isInverted ? .black : .white
    }

    private var secondaryTextColor: Color {
        isInverted ? Color(white: 0.4) : Color(white: 0.7)
    }

    private var cardBackgroundColor: Color {
        isInverted ? Color(white: 0.96) : Color(white: 0.13)
    }

    var body: some View {
        VStack(spacing: 8) {
            // Header with controls
            VStack(spacing: 8) {
                HStack(spacing: 16) {
                    // Language picker
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Language")
                            .font(.caption)
                            .foregroundColor(secondaryTextColor)
                        Picker("Language", selection: $currentLanguage) {
                            ForEach(AlphabetData.availableLanguages, id: \.self) { lang in
                                Text(lang).tag(lang)
                            }
                        }
                        .pickerStyle(.menu)
                        .onChange(of: currentLanguage) {
                            resetForNewLanguage()
                        }
                    }

                    // Letter count picker
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Letters")
                            .font(.caption)
                            .foregroundColor(secondaryTextColor)
                        Picker("Letters", selection: $letterCount) {
                            ForEach(2...7, id: \.self) { count in
                                Text("\(count)").tag(count)
                            }
                        }
                        .pickerStyle(.menu)
                        .onChange(of: letterCount) {
                            startRound()
                        }
                    }
                }

                Toggle("Include combined forms", isOn: $includeCombinedForms)
                    .font(.subheadline)
                    .foregroundColor(textColor)
                    .onChange(of: includeCombinedForms) {
                        startRound()
                    }
            }
            .padding(12)
            .background(cardBackgroundColor)
            .cornerRadius(12)

            // Points display
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

            // Game area
            HStack(alignment: .top, spacing: 16) {
                // Letters column
                VStack(spacing: 4) {
                    Text("LETTERS")
                        .font(.caption)
                        .foregroundColor(secondaryTextColor)
                        .tracking(1)

                    ForEach(currentRound) { letter in
                        LetterCard(
                            text: AlphabetData.displayLetter(letter.letter),
                            isMatched: matchedLetters.contains(letter.letter),
                            isSelected: selectedLetter?.letter == letter.letter,
                            fontSize: 37
                        )
                        .onTapGesture {
                            if !matchedLetters.contains(letter.letter) {
                                selectedLetter = letter
                                messageText = ""
                            }
                        }
                    }
                }
                .frame(maxWidth: .infinity)

                // Phonetics column
                VStack(spacing: 4) {
                    Text("PHONETICS")
                        .font(.caption)
                        .foregroundColor(secondaryTextColor)
                        .tracking(1)

                    ForEach(shuffledPhonetics, id: \.self) { phonetic in
                        PhoneticCard(
                            text: phonetic,
                            isMatched: isPhoneticMatched(phonetic)
                        )
                        .onTapGesture {
                            handlePhoneticTap(phonetic)
                        }
                    }
                }
                .frame(maxWidth: .infinity)
            }
            .padding(12)
            .background(cardBackgroundColor)
            .cornerRadius(12)
            .frame(maxHeight: .infinity)

            // Message area
            Text(messageText)
                .font(.subheadline)
                .foregroundColor(messageColor)
                .frame(maxWidth: .infinity)
                .padding(8)
        }
        .padding(12)
        .background(backgroundColor)
        .navigationTitle("Practice Alphabets")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            startRound()
        }
    }

    private func isPhoneticMatched(_ phonetic: String) -> Bool {
        currentRound.first { $0.phonetic == phonetic && matchedLetters.contains($0.letter) } != nil
    }

    private func handlePhoneticTap(_ phonetic: String) {
        guard let letter = selectedLetter else {
            messageText = "Select a letter first"
            messageColor = .orange
            return
        }

        if matchedLetters.contains(letter.letter) {
            return
        }

        if letter.phonetic == phonetic {
            // Correct match
            matchedLetters.insert(letter.letter)
            selectedLetter = nil

            if matchedLetters.count == currentRound.count {
                // Round complete
                let earnedPoints = hasMistake ? 1 : 10
                points += earnedPoints

                if hasMistake {
                    messageText = "Correct! +1 point. Next round in 3 seconds..."
                    perfectStreak = false
                } else {
                    messageText = "Perfect! +10 points! Next round in 3 seconds..."
                    // Add to mastered letters
                    for letter in currentRound {
                        masteredLetters.insert(letter.letter)
                    }
                    checkForMastery()
                }
                messageColor = .green

                DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                    startRound()
                }
            }
        } else {
            // Wrong match
            hasMistake = true
            messageText = "Try again!"
            messageColor = .red
        }
    }

    private func startRound() {
        let alphabet = AlphabetData.getAlphabet(for: currentLanguage, includeCombinedForms: includeCombinedForms)
        currentRound = AlphabetData.getUniqueRandomItems(from: alphabet, count: letterCount)
        shuffledPhonetics = currentRound.map { $0.phonetic }.shuffled()
        matchedLetters = []
        selectedLetter = nil
        hasMistake = false

        if isFirstRound {
            messageText = "Tap a letter, then tap its matching sound"
            messageColor = .gray
            isFirstRound = false
        } else {
            messageText = ""
        }
    }

    private func resetForNewLanguage() {
        points = 0
        masteredLetters = []
        perfectStreak = true
        hasAchievedMastery = false
        startRound()
    }

    private func checkForMastery() {
        if hasAchievedMastery || !perfectStreak { return }

        let alphabet = AlphabetData.getAlphabet(for: currentLanguage, includeCombinedForms: includeCombinedForms)
        let allLetters = Set(alphabet.map { $0.letter })

        if masteredLetters.isSuperset(of: allLetters) {
            hasAchievedMastery = true
            showMasteryCelebration()
        }
    }

    private func showMasteryCelebration() {
        showMasteryGlow = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            showMasteryGlow = false
        }
    }
}

struct LetterCard: View {
    let text: String
    let isMatched: Bool
    let isSelected: Bool
    var fontSize: CGFloat = 37

    var body: some View {
        Text(text)
            .font(.system(size: fontSize, weight: .medium))
            .foregroundColor(isMatched ? .white : .black)
            .frame(minWidth: 60, minHeight: 57)
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

struct PhoneticCard: View {
    let text: String
    let isMatched: Bool

    var body: some View {
        Text(text)
            .font(.system(size: 22, weight: .medium))
            .foregroundColor(isMatched ? .white : .black)
            .frame(minWidth: 80, minHeight: 57)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isMatched ? Color.green : Color(white: 0.95))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
            )
    }
}

#Preview {
    NavigationStack {
        PracticeAlphabetsView()
    }
}
