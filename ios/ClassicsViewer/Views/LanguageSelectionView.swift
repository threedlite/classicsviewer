import SwiftUI

struct LanguageSelectionView: View {
    @EnvironmentObject var appState: AppState
    @State private var customLanguages: [CustomLanguageConfig] = []

    var body: some View {
        VStack(spacing: 30) {
            Spacer()

            Text("Select Language")
                .font(.largeTitle)
                .fontWeight(.bold)

            Spacer()

            ScrollView {
                VStack(spacing: 20) {
                    // All language buttons (including Greek and Latin)
                    ForEach(customLanguages) { language in
                        Button(action: {
                            appState.selectLanguage(.custom(language.id, language.displayName))
                        }) {
                            Text(language.displayName)
                                .font(.title2)
                                .fontWeight(.semibold)
                                .foregroundColor(textColorForBackground(language.swiftUIColor))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 30)
                                .background(language.swiftUIColor)
                                .cornerRadius(8)
                        }
                    }
                }
                .padding(.horizontal, 40)
            }

            Spacer()
            Spacer()
        }
        .onAppear {
            Task {
                await autoDetectLanguages()
                loadCustomLanguages()
            }
        }
    }

    private func loadCustomLanguages() {
        customLanguages = UserDefaults.standard.customLanguages
    }

    private func autoDetectLanguages() async {
        do {
            // Preferred order for auto-detected languages (matching Android exactly)
            let preferredOrder = [
                "greek", "latin", "sumerian", "akkadian",
                "sanskrit", "persian", "hebrew", "arabic",
                "coptic", "syriac", "italian", "pali", "norse", "old_english"
            ]

            // One-time migration: fix any existing ordering issues (matches Android)
            if !UserDefaults.standard.hasFixedLanguageOrder {
                print("Running one-time language order fix")
                UserDefaults.standard.reorderLanguagesByPreferredOrder(preferredOrder)
                UserDefaults.standard.hasFixedLanguageOrder = true
            }

            // Get all distinct languages from the database
            let authorDAO = AuthorDAO()
            let allLanguages = try await authorDAO.getAllLanguages()

            print("Auto-detecting languages from database: \(allLanguages)")

            // Get existing custom languages and suppressed languages
            let existingCustomLanguages = UserDefaults.standard.customLanguages
            let existingLanguageIds = Set(existingCustomLanguages.map { $0.id })
            let suppressedLanguages = UserDefaults.standard.suppressedLanguages

            print("Existing languages: \(existingLanguageIds)")
            print("Suppressed languages: \(suppressedLanguages)")

            var languagesAdded = false

            // First, add languages in preferred order if they exist in database and not already added
            for languageId in preferredOrder {
                if allLanguages.contains(languageId)
                    && !existingLanguageIds.contains(languageId)
                    && !suppressedLanguages.contains(languageId) {
                    let displayName = convertLanguageIdToDisplayName(languageId)
                    let color = generateDefaultColor(for: languageId)

                    let customLanguage = CustomLanguageConfig(
                        id: languageId,
                        displayName: displayName,
                        color: color
                    )
                    UserDefaults.standard.addCustomLanguage(customLanguage)

                    print("Auto-added language: \(languageId) -> \(displayName)")
                    languagesAdded = true
                }
            }

            // Then add any remaining languages not in preferred order
            for languageId in allLanguages {
                if !preferredOrder.contains(languageId)
                    && !existingLanguageIds.contains(languageId)
                    && !suppressedLanguages.contains(languageId) {
                    let displayName = convertLanguageIdToDisplayName(languageId)
                    let color = generateDefaultColor(for: languageId)

                    let customLanguage = CustomLanguageConfig(
                        id: languageId,
                        displayName: displayName,
                        color: color
                    )
                    UserDefaults.standard.addCustomLanguage(customLanguage)

                    print("Auto-added language (not in preferred order): \(languageId) -> \(displayName)")
                    languagesAdded = true
                }
            }

            // If languages were added, reorder by preferred order (matches Android)
            if languagesAdded {
                UserDefaults.standard.reorderLanguagesByPreferredOrder(preferredOrder)
            }

            // Refresh the UI
            loadCustomLanguages()
        } catch {
            print("Error auto-detecting languages: \(error)")
        }
    }

    private func convertLanguageIdToDisplayName(_ languageId: String) -> String {
        // Replace underscores with spaces, then capitalize each word
        return languageId.replacingOccurrences(of: "_", with: " ")
            .split(separator: " ")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

    private func generateDefaultColor(for languageId: String) -> Int {
        // Generate colors matching Android (Loeb-style aesthetic)
        switch languageId.lowercased() {
        case "greek":
            return 0xFF5A8A5C     // Loeb Greek green
        case "latin":
            return 0xFFB85450     // Loeb Latin red
        case "sanskrit":
            return 0xFFC39B5A     // Desaturated saffron
        case "hebrew":
            return 0xFF6B7BA8     // Desaturated indigo
        case "arabic":
            return 0xFFDCDCDC     // Light grey/white
        case "persian":
            return 0xFF9B7BA8     // Desaturated purple
        case "sumerian":
            return 0xFF5A73AA     // Desaturated blue
        case "akkadian":
            return 0xFFAF9B7D     // Desaturated tan
        case "coptic":
            return 0xFF5A9B8A     // Egyptian teal
        case "syriac":
            return 0xFF9B7B5A     // Florentine brown
        case "italian":
            return 0xFFA8727B     // Dusty rose
        case "pali":
            return 0xFF7EABC9     // Light blue
        case "norse":
            return 0xFF5A5A5A     // Dark grey
        case "old_english":
            return 0xFFB78700     // Gold
        default:
            return 0xFF808080     // Grey for unknown languages
        }
    }

    private func textColorForBackground(_ color: Color) -> Color {
        let uiColor = UIColor(color)
        var red: CGFloat = 0
        var green: CGFloat = 0
        var blue: CGFloat = 0
        var alpha: CGFloat = 0

        uiColor.getRed(&red, green: &green, blue: &blue, alpha: &alpha)

        let brightness = Int((red * 255 * 299 + green * 255 * 587 + blue * 255 * 114) / 1000)
        return brightness > 128 ? .black : .white
    }
}

struct LanguageSelectionView_Previews: PreviewProvider {
    static var previews: some View {
        LanguageSelectionView()
            .environmentObject(AppState())
    }
}