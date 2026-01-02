import SwiftUI

struct ExportOptionsView: View {
    @Environment(\.dismiss) private var dismiss

    private let maxExportLines = 5000

    let authorName: String
    let workTitle: String
    let bookLabel: String
    let totalLines: Int
    let currentStartLine: Int
    let currentEndLine: Int
    let contentType: ExportContentType
    let translator: String?
    let language: String
    let onExport: (ExportFormat, Int, Int) -> Void

    @State private var selectedFormat: ExportFormat = .pdf
    @State private var startLine: Int
    @State private var endLine: Int
    @State private var useEntireBook: Bool = true

    init(
        authorName: String,
        workTitle: String,
        bookLabel: String,
        totalLines: Int,
        currentStartLine: Int,
        currentEndLine: Int,
        contentType: ExportContentType,
        translator: String?,
        language: String,
        onExport: @escaping (ExportFormat, Int, Int) -> Void
    ) {
        self.authorName = authorName
        self.workTitle = workTitle
        self.bookLabel = bookLabel
        self.totalLines = totalLines
        self.currentStartLine = currentStartLine
        self.currentEndLine = currentEndLine
        self.contentType = contentType
        self.translator = translator
        self.language = language
        self.onExport = onExport

        _startLine = State(initialValue: currentStartLine)
        _endLine = State(initialValue: currentEndLine)

        // If book is too large, force range selection
        if totalLines > 5000 {
            _useEntireBook = State(initialValue: false)
        }
    }

    private var isTooLarge: Bool {
        totalLines > maxExportLines
    }

    private var selectedLineCount: Int {
        useEntireBook ? totalLines : max(0, endLine - startLine + 1)
    }

    private var isRangeTooLarge: Bool {
        selectedLineCount > maxExportLines
    }

    var body: some View {
        NavigationView {
            Form {
                // Format Selection
                Section("Format") {
                    Picker("Format", selection: $selectedFormat) {
                        Text("PDF").tag(ExportFormat.pdf)
                        Text("TXT").tag(ExportFormat.txt)
                        Text("CSV").tag(ExportFormat.csv)
                    }
                    .pickerStyle(.segmented)
                }

                // Range Selection
                Section("Line Range") {
                    if isTooLarge {
                        Text("Book has \(totalLines) lines. Select a range of \(maxExportLines) or fewer to export.")
                            .font(.caption)
                            .foregroundColor(.orange)
                    } else {
                        Toggle("Entire Book (1-\(totalLines))", isOn: $useEntireBook)
                            .onChange(of: useEntireBook) { _, newValue in
                                if newValue {
                                    startLine = 1
                                    endLine = totalLines
                                } else {
                                    startLine = currentStartLine
                                    endLine = currentEndLine
                                }
                            }
                    }

                    if !useEntireBook || isTooLarge {
                        HStack {
                            Text("From")
                            TextField("Start", value: $startLine, format: .number)
                                .textFieldStyle(.roundedBorder)
                                .keyboardType(.numberPad)
                                .frame(width: 80)

                            Text("to")

                            TextField("End", value: $endLine, format: .number)
                                .textFieldStyle(.roundedBorder)
                                .keyboardType(.numberPad)
                                .frame(width: 80)
                        }

                        if isRangeTooLarge {
                            Text("Range too large (\(selectedLineCount) lines). Maximum is \(maxExportLines).")
                                .font(.caption)
                                .foregroundColor(.red)
                        }
                    }
                }

                // Preview Info
                Section("Export Preview") {
                    LabeledContent("Author", value: authorName)
                    LabeledContent("Work", value: workTitle)
                    LabeledContent("Book", value: bookLabel)

                    let lineCount = (useEntireBook ? totalLines : (endLine - startLine + 1))
                    let rangeText = useEntireBook ? "1-\(totalLines)" : "\(startLine)-\(endLine)"
                    LabeledContent("Lines", value: "\(rangeText) (\(lineCount) lines)")

                    if let translator = translator {
                        LabeledContent("Translator", value: translator)
                    }
                    LabeledContent("Content", value: contentTypeLabel)
                }
            }
            .navigationTitle("Export")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Export") {
                        let validStart = max(1, min(useEntireBook ? 1 : startLine, totalLines))
                        let validEnd = max(validStart, min(useEntireBook ? totalLines : endLine, totalLines))
                        onExport(selectedFormat, validStart, validEnd)
                        dismiss()
                    }
                    .disabled(isRangeTooLarge)
                }
            }
        }
    }

    private var contentTypeLabel: String {
        switch contentType {
        case .source:
            return "\(language.capitalized) Text"
        case .translation:
            return "Translation"
        }
    }
}
