import SwiftUI
import UniformTypeIdentifiers

// TXT Document for file export
struct TxtDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.plainText] }

    var content: String

    init(content: String) {
        self.content = content
    }

    init(configuration: ReadConfiguration) throws {
        if let data = configuration.file.regularFileContents,
           let string = String(data: data, encoding: .utf8) {
            content = string
        } else {
            content = ""
        }
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        // Add UTF-8 BOM for proper encoding detection in browsers/apps
        var data = Data([0xEF, 0xBB, 0xBF])
        data.append(content.data(using: .utf8) ?? Data())
        return FileWrapper(regularFileWithContents: data)
    }
}

// PDF Document for file export
struct PdfDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.pdf] }

    var data: Data

    init(data: Data) {
        self.data = data
    }

    init(configuration: ReadConfiguration) throws {
        data = configuration.file.regularFileContents ?? Data()
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}

// Wrapper view for PDF export
struct PdfExporterView: View {
    @Environment(\.dismiss) private var dismiss
    let document: PdfDocument
    let filename: String
    let onResult: (Result<URL, Error>) -> Void
    @State private var showingExporter = false

    var body: some View {
        VStack {
            ProgressView("Preparing export...")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(UIColor.systemBackground))
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                showingExporter = true
            }
        }
        .fileExporter(
            isPresented: $showingExporter,
            document: document,
            contentType: .pdf,
            defaultFilename: filename
        ) { result in
            onResult(result)
            dismiss()
        }
    }
}

// Wrapper view for TXT export
struct TxtExporterView: View {
    @Environment(\.dismiss) private var dismiss
    let document: TxtDocument
    let filename: String
    let onResult: (Result<URL, Error>) -> Void
    @State private var showingExporter = false

    var body: some View {
        VStack {
            ProgressView("Preparing export...")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(UIColor.systemBackground))
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                showingExporter = true
            }
        }
        .fileExporter(
            isPresented: $showingExporter,
            document: document,
            contentType: .plainText,
            defaultFilename: filename
        ) { result in
            onResult(result)
            dismiss()
        }
    }
}

// Wrapper view for CSV export
struct CsvExporterView: View {
    @Environment(\.dismiss) private var dismiss
    let document: CSVDocument
    let filename: String
    let onResult: (Result<URL, Error>) -> Void
    @State private var showingExporter = false

    var body: some View {
        VStack {
            ProgressView("Preparing export...")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(UIColor.systemBackground))
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                showingExporter = true
            }
        }
        .fileExporter(
            isPresented: $showingExporter,
            document: document,
            contentType: .csv,
            defaultFilename: filename
        ) { result in
            onResult(result)
            dismiss()
        }
    }
}
