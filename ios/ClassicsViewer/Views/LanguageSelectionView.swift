import SwiftUI

struct LanguageSelectionView: View {
    @EnvironmentObject var appState: AppState
    @State private var customLanguages: [CustomLanguageConfig] = []

    // Android Material Design colors
    let greekColor = Color(red: 0.298, green: 0.686, blue: 0.314) // #4CAF50 Material Green 500
    let latinColor = Color(red: 0.957, green: 0.263, blue: 0.212) // #F44336 Material Red 500

    var body: some View {
        VStack(spacing: 30) {
            Spacer()

            Text("Select Language")
                .font(.largeTitle)
                .fontWeight(.bold)

            Spacer()

            ScrollView {
                VStack(spacing: 20) {
                    // Greek button
                    Button(action: {
                        appState.selectLanguage(.greek)
                    }) {
                        Text("Greek")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 30)
                            .background(greekColor)
                            .cornerRadius(8)
                    }

                    // Latin button
                    Button(action: {
                        appState.selectLanguage(.latin)
                    }) {
                        Text("Latin")
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 30)
                            .background(latinColor)
                            .cornerRadius(8)
                    }

                    // Custom language buttons
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
            loadCustomLanguages()
        }
    }

    private func loadCustomLanguages() {
        customLanguages = UserDefaults.standard.customLanguages
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