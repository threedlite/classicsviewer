import SwiftUI

// Wrapper to handle both Add (nil) and Edit (language) cases
struct LanguageDialogItem: Identifiable {
    let id = UUID()
    let language: CustomLanguageConfig?
}

struct ManageLanguagesView: View {
    @State private var customLanguages: [CustomLanguageConfig] = []
    @State private var dialogItem: LanguageDialogItem?
    @State private var showingDeleteAlert = false
    @State private var languageToDelete: CustomLanguageConfig?
    @State private var showingToast = false
    @State private var toastMessage = ""

    var body: some View {
        VStack(spacing: 0) {
            // Add Language button at top (matches Android)
            Button(action: {
                dialogItem = LanguageDialogItem(language: nil)
            }) {
                Text("Add Language")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
            .padding()

            // Language list with drag-and-drop reordering (matches Android RecyclerView)
            if customLanguages.isEmpty {
                Spacer()
                Text("No custom languages added")
                    .foregroundColor(.secondary)
                Spacer()
            } else {
                List {
                    ForEach(customLanguages) { language in
                        CustomLanguageRow(
                            language: language,
                            onEdit: {
                                dialogItem = LanguageDialogItem(language: language)
                            },
                            onDelete: {
                                languageToDelete = language
                                showingDeleteAlert = true
                            }
                        )
                    }
                    .onMove { from, to in
                        customLanguages.move(fromOffsets: from, toOffset: to)
                        saveCustomLanguagesOrder()
                    }
                }
                .listStyle(PlainListStyle())
                .environment(\.defaultMinListRowHeight, 0)
            }
        }
        .navigationTitle("Manage Languages")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if !customLanguages.isEmpty {
                EditButton()  // Enables drag-and-drop reordering
            }
        }
        .onAppear {
            loadCustomLanguages()
        }
        .sheet(item: $dialogItem) { item in
            AddEditLanguageDialog(
                existingLanguage: item.language,
                onSave: { language in
                    UserDefaults.standard.addCustomLanguage(language)
                    loadCustomLanguages()
                    showToast("Language configuration saved")
                    dialogItem = nil
                },
                onCancel: {
                    dialogItem = nil
                }
            )
        }
        .alert("Delete Language", isPresented: $showingDeleteAlert, presenting: languageToDelete) { language in
            Button("Cancel", role: .cancel) {
                languageToDelete = nil
            }
            Button("Delete", role: .destructive) {
                deleteLanguage(language)
                languageToDelete = nil
            }
        } message: { language in
            Text("Delete \(language.displayName)?")
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

    private func saveCustomLanguagesOrder() {
        // Save the reordered list back to UserDefaults
        if let encoded = try? JSONEncoder().encode(customLanguages) {
            UserDefaults.standard.set(encoded, forKey: "customLanguages")
        }
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
}

// Row for displaying custom languages - matches Android item_custom_language.xml
struct CustomLanguageRow: View {
    let language: CustomLanguageConfig
    let onEdit: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Drag handle indicator (matches Android dragHandle)
            Image(systemName: "line.3.horizontal")
                .foregroundColor(.gray)
                .opacity(0.5)

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

            Spacer()

            // Edit button
            Button(action: {
                print("Edit button tapped for \(language.id)")
                onEdit()
            }) {
                Text("Edit")
                    .foregroundColor(textColorForBackground(language.swiftUIColor))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.black.opacity(0.1))
                    .cornerRadius(4)
            }
            .buttonStyle(BorderlessButtonStyle())

            // Delete button
            Button(action: {
                print("Delete button tapped for \(language.id)")
                onDelete()
            }) {
                Text("Delete")
                    .foregroundColor(textColorForBackground(language.swiftUIColor))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.black.opacity(0.1))
                    .cornerRadius(4)
            }
            .buttonStyle(BorderlessButtonStyle())
        }
        .padding(.vertical, 12)
        .padding(.horizontal, 12)
        .background(language.swiftUIColor)
        .cornerRadius(8)
        .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
        .listRowBackground(Color.clear)
        .contentShape(Rectangle())
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

// Add/Edit Language Dialog (matches Android dialog_add_edit_language.xml)
struct AddEditLanguageDialog: View {
    let existingLanguage: CustomLanguageConfig?
    let onSave: (CustomLanguageConfig) -> Void
    let onCancel: () -> Void

    @Environment(\.dismiss) var dismiss
    @State private var languageId: String
    @State private var displayName: String
    @State private var oldLanguageId: String
    @State private var selectedColor: Color
    @State private var selectedColorInt: Int
    @State private var showingColorPicker = false

    init(existingLanguage: CustomLanguageConfig?, onSave: @escaping (CustomLanguageConfig) -> Void, onCancel: @escaping () -> Void) {
        self.existingLanguage = existingLanguage
        self.onSave = onSave
        self.onCancel = onCancel

        // Initialize state from existing language or empty defaults
        if let existing = existingLanguage {
            _languageId = State(initialValue: existing.id)
            _displayName = State(initialValue: existing.displayName)
            _oldLanguageId = State(initialValue: existing.id)
            _selectedColorInt = State(initialValue: existing.color)
            _selectedColor = State(initialValue: existing.swiftUIColor)
        } else {
            // Empty fields for adding new language
            _languageId = State(initialValue: "")
            _displayName = State(initialValue: "")
            _oldLanguageId = State(initialValue: "")
            _selectedColorInt = State(initialValue: 0xFF808080)
            _selectedColor = State(initialValue: .gray)
        }
    }

    var body: some View {
        NavigationView {
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
                            .disabled(existingLanguage != nil)  // Don't allow changing ID when editing
                            .onChange(of: languageId) { newValue in
                                // Auto-populate display name if it's empty (matching Android)
                                if displayName.isEmpty || displayName == convertLanguageIdToDisplayName(oldLanguageId) {
                                    displayName = convertLanguageIdToDisplayName(newValue)
                                }
                                oldLanguageId = newValue
                            }
                    }

                    // Display Name Input
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Display Name (e.g., Akkadian, Sumerian)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        TextField("Display Name", text: $displayName)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
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
                }
                .padding()
            }
            .navigationTitle(existingLanguage == nil ? "Add Language" : "Edit Language")
            .navigationBarTitleDisplayMode(.inline)
            .navigationBarItems(
                leading: Button("Cancel") {
                    dismiss()
                    onCancel()
                },
                trailing: Button("Save") {
                    saveLanguage()
                }
            )
            .sheet(isPresented: $showingColorPicker) {
                ColorPickerView(selectedColor: $selectedColor, selectedColorInt: $selectedColorInt)
            }
        }
    }

    private func saveLanguage() {
        let trimmedId = languageId.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let trimmedName = displayName.trimmingCharacters(in: .whitespacesAndNewlines)

        // Validation
        guard !trimmedId.isEmpty else { return }
        guard !trimmedName.isEmpty else { return }
        guard trimmedId != "greek" && trimmedId != "latin" else { return }

        // Create and save the custom language
        let customLanguage = CustomLanguageConfig(
            id: trimmedId,
            displayName: trimmedName,
            color: selectedColorInt
        )

        onSave(customLanguage)
        dismiss()
    }

    private func convertLanguageIdToDisplayName(_ languageId: String) -> String {
        return languageId.replacingOccurrences(of: "_", with: " ")
            .split(separator: " ")
            .map { $0.capitalized }
            .joined(separator: " ")
    }

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

        return Int((red * 255 * 299 + green * 255 * 587 + blue * 255 * 114) / 1000)
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
