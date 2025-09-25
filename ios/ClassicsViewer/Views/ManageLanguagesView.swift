import SwiftUI

struct ManageLanguagesView: View {
    @State private var languageId = "akkadian"  // Default value matches Android
    @State private var displayName = "Akkadian"  // Default value matches Android
    @State private var selectedColor = Color.gray
    @State private var selectedColorInt: Int = 0xFF808080
    @State private var showingColorPicker = false
    @State private var customLanguages: [CustomLanguageConfig] = []
    @State private var showingDeleteAlert = false
    @State private var languageToDelete: CustomLanguageConfig?
    @State private var showingToast = false
    @State private var toastMessage = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Language ID Input
                VStack(alignment: .leading, spacing: 4) {
                    Text("Language ID (e.g., akkadian, sumerian)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    TextField("Language ID", text: $languageId)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .textCase(.lowercase)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                }

                // Display Name Input
                VStack(alignment: .leading, spacing: 4) {
                    Text("Display Name (e.g., Akkadian, Sumerian)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    TextField("Display Name", text: $displayName)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .onChange(of: displayName) { _ in
                            // Update preview when name changes
                        }
                }

                // Button Color Section
                VStack(alignment: .leading, spacing: 12) {
                    Text("Button Color")
                        .font(.headline)
                        .padding(.top, 8)

                    HStack(spacing: 16) {
                        // Color preview box
                        RoundedRectangle(cornerRadius: 8)
                            .fill(selectedColor)
                            .frame(width: 60, height: 60)
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                            )

                        Button("Pick Color") {
                            showingColorPicker = true
                        }
                        .buttonStyle(.bordered)
                    }
                }

                // Preview Section
                VStack(alignment: .leading, spacing: 12) {
                    Text("Preview")
                        .font(.headline)
                        .padding(.top, 8)

                    // Preview card matching Android's MaterialCardView
                    Button(action: {}) {
                        Text(displayName.isEmpty ? "Language" : displayName)
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundColor(textColorForBackground(selectedColor))
                            .frame(maxWidth: .infinity)
                            .frame(height: 80)
                    }
                    .background(selectedColor)
                    .cornerRadius(8)
                    .disabled(true)
                }

                // Save Button
                Button(action: saveLanguageConfiguration) {
                    Text("Save Language Configuration")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.accentColor)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }
                .padding(.top, 16)

                // Custom Languages List
                if !customLanguages.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Custom Languages")
                            .font(.headline)
                            .padding(.top, 24)

                        ForEach(customLanguages) { language in
                            CustomLanguageRow(
                                language: language,
                                onDelete: {
                                    languageToDelete = language
                                    showingDeleteAlert = true
                                }
                            )
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle("Manage Languages")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            loadCustomLanguages()
        }
        .sheet(isPresented: $showingColorPicker) {
            ColorPickerView(selectedColor: $selectedColor, selectedColorInt: $selectedColorInt)
        }
        .alert("Delete Language", isPresented: $showingDeleteAlert) {
            Button("Cancel", role: .cancel) {}
            Button("Delete", role: .destructive) {
                if let language = languageToDelete {
                    deleteLanguage(language)
                }
            }
        } message: {
            Text("Delete \(languageToDelete?.displayName ?? "")?")
        }
        .overlay(
            // Toast notification
            VStack {
                Spacer()
                if showingToast {
                    Text(toastMessage)
                        .padding()
                        .background(Color.black.opacity(0.8))
                        .foregroundColor(.white)
                        .cornerRadius(8)
                        .padding(.bottom, 50)
                        .transition(.move(edge: .bottom))
                }
            }
            .animation(.easeInOut(duration: 0.3), value: showingToast)
        )
    }

    private func loadCustomLanguages() {
        customLanguages = UserDefaults.standard.customLanguages
    }

    private func saveLanguageConfiguration() {
        let trimmedId = languageId.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let trimmedName = displayName.trimmingCharacters(in: .whitespacesAndNewlines)

        // Validation
        if trimmedId.isEmpty {
            showToast("Please enter a language ID")
            return
        }

        if trimmedName.isEmpty {
            showToast("Please enter a display name")
            return
        }

        // Don't allow overriding Greek or Latin
        if trimmedId == "greek" || trimmedId == "latin" {
            showToast("Cannot override built-in languages")
            return
        }

        // Create and save the custom language
        let customLanguage = CustomLanguageConfig(
            id: trimmedId,
            displayName: trimmedName,
            color: selectedColorInt
        )

        UserDefaults.standard.addCustomLanguage(customLanguage)

        showToast("Language configuration saved")

        // Reset form to defaults matching Android
        languageId = "akkadian"
        displayName = "Akkadian"
        selectedColor = .gray
        selectedColorInt = 0xFF808080

        // Reload the list
        loadCustomLanguages()
    }

    private func deleteLanguage(_ language: CustomLanguageConfig) {
        UserDefaults.standard.removeCustomLanguage(withId: language.id)
        loadCustomLanguages()
        showToast("Language deleted")
    }

    private func showToast(_ message: String) {
        toastMessage = message
        showingToast = true

        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            showingToast = false
        }
    }

    // Calculate text color based on background brightness (matching Android)
    private func textColorForBackground(_ color: Color) -> Color {
        let brightness = getBrightness(color)
        return brightness > 128 ? .black : .white
    }

    private func getBrightness(_ color: Color) -> Int {
        let uiColor = UIColor(color)
        var red: CGFloat = 0
        var green: CGFloat = 0
        var blue: CGFloat = 0
        var alpha: CGFloat = 0

        uiColor.getRed(&red, green: &green, blue: &blue, alpha: &alpha)

        // Calculate perceived brightness using standard formula (same as Android)
        return Int((red * 255 * 299 + green * 255 * 587 + blue * 255 * 114) / 1000)
    }
}

// Row for displaying custom languages - matches Android item_custom_language.xml
struct CustomLanguageRow: View {
    let language: CustomLanguageConfig
    let onDelete: () -> Void

    var body: some View {
        ZStack {
            // Card background with custom color
            RoundedRectangle(cornerRadius: 8)
                .fill(language.swiftUIColor)
                .shadow(radius: 2)

            HStack {
                // Language info on the left
                VStack(alignment: .leading, spacing: 4) {
                    Text(language.displayName)
                        .font(.system(size: 18))
                        .fontWeight(.bold)
                        .foregroundColor(textColorForBackground(language.swiftUIColor))

                    Text("ID: \(language.id)")
                        .font(.system(size: 14))
                        .foregroundColor(textColorForBackground(language.swiftUIColor))
                }
                .padding(.leading, 12)

                Spacer()

                // Delete button on the right
                Button("Delete") {
                    onDelete()
                }
                .foregroundColor(textColorForBackground(language.swiftUIColor))
                .padding(.trailing, 12)
            }
            .padding(.vertical, 12)
        }
        .frame(height: 70)
        .padding(.bottom, 8)
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

// Color Picker View matching Android's dialog
struct ColorPickerView: View {
    @Binding var selectedColor: Color
    @Binding var selectedColorInt: Int
    @Environment(\.dismiss) var dismiss

    @State private var red: Double = 128
    @State private var green: Double = 128
    @State private var blue: Double = 128

    var hexValue: String {
        String(format: "#%02X%02X%02X", Int(red), Int(green), Int(blue))
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Color preview
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(red: red/255, green: green/255, blue: blue/255))
                    .frame(height: 100)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )

                // Red Slider - matches Android layout
                VStack(alignment: .leading, spacing: 4) {
                    Text("Red")
                        .font(.system(size: 14))
                    HStack {
                        Slider(value: $red, in: 0...255, step: 1)
                        Text("\(Int(red))")
                            .frame(width: 40)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.bottom, 16)

                // Green Slider - matches Android layout
                VStack(alignment: .leading, spacing: 4) {
                    Text("Green")
                        .font(.system(size: 14))
                    HStack {
                        Slider(value: $green, in: 0...255, step: 1)
                        Text("\(Int(green))")
                            .frame(width: 40)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.bottom, 16)

                // Blue Slider - matches Android layout
                VStack(alignment: .leading, spacing: 4) {
                    Text("Blue")
                        .font(.system(size: 14))
                    HStack {
                        Slider(value: $blue, in: 0...255, step: 1)
                        Text("\(Int(blue))")
                            .frame(width: 40)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(.bottom, 16)

                // Hex value display - matches Android layout
                Text(hexValue)
                    .font(.system(size: 16))
                    .fontWeight(.bold)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 8)

                Spacer()
            }
            .padding()
            .navigationTitle("Pick Button Color")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    dismiss()
                },
                trailing: Button("OK") {
                    selectedColor = Color(red: red/255, green: green/255, blue: blue/255)
                    selectedColorInt = CustomLanguageConfig.colorToInt(red: red/255, green: green/255, blue: blue/255)
                    dismiss()
                }
            )
            .onAppear {
                // Initialize sliders from current color
                let uiColor = UIColor(selectedColor)
                var r: CGFloat = 0
                var g: CGFloat = 0
                var b: CGFloat = 0
                var a: CGFloat = 0
                uiColor.getRed(&r, green: &g, blue: &b, alpha: &a)

                red = Double(r * 255)
                green = Double(g * 255)
                blue = Double(b * 255)
            }
        }
    }
}

struct ManageLanguagesView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            ManageLanguagesView()
        }
    }
}