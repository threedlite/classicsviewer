import Foundation
import UIKit
import PDFKit

enum ExportFormat {
    case csv
    case txt
    case pdf
}

enum ExportContentType {
    case source
    case translation
}

struct ExportRequest {
    let format: ExportFormat
    let contentType: ExportContentType
    let authorName: String
    let workTitle: String
    let bookLabel: String
    let workId: String
    let startLine: Int
    let endLine: Int
    let translator: String?
    let language: String
}

class TextExporter {

    // MARK: - CSV Export

    static func generateCsvContent(
        request: ExportRequest,
        lines: [TextLine]? = nil,
        translations: [TranslationSegment]? = nil
    ) -> String {
        var content = ""

        // CSV header
        content += "line_number,text\n"

        // Content
        switch request.contentType {
        case .source:
            if let lines = lines {
                for line in lines {
                    let text = csvEscape(line.lineText)
                    content += "\(line.lineNumber),\(text)\n"
                }
            }

        case .translation:
            if let translations = translations {
                for segment in translations {
                    let lineNum = segment.endLine != nil && segment.endLine != segment.startLine
                        ? "\(segment.startLine)-\(segment.endLine!)"
                        : "\(segment.startLine)"
                    let text = csvEscape(segment.translationText)
                    content += "\(lineNum),\(text)\n"
                }
            }
        }

        return content
    }

    private static func csvEscape(_ text: String) -> String {
        // If text contains comma, quote, or newline, wrap in quotes and escape quotes
        if text.contains(",") || text.contains("\"") || text.contains("\n") {
            let escaped = text.replacingOccurrences(of: "\"", with: "\"\"")
            return "\"\(escaped)\""
        }
        return text
    }

    // MARK: - TXT Export

    static func generateTxtContent(
        request: ExportRequest,
        lines: [TextLine]? = nil,
        translations: [TranslationSegment]? = nil
    ) -> String {
        var content = ""

        // Header
        content += "\(request.authorName) - \(request.workTitle)\n"
        content += "\(request.bookLabel), Lines \(request.startLine)-\(request.endLine)\n"
        if let translator = request.translator {
            content += "Translation by \(translator)\n"
        }
        content += "\n"

        // Content
        switch request.contentType {
        case .source:
            if let lines = lines {
                for line in lines {
                    var lineText = String(format: "%5d  ", line.lineNumber)
                    if let speaker = line.speaker, !speaker.isEmpty {
                        lineText += "[\(speaker)] "
                    }
                    lineText += line.lineText
                    content += lineText + "\n"
                }
            }

        case .translation:
            if let translations = translations {
                for segment in translations {
                    let range = segment.endLine != nil && segment.endLine != segment.startLine
                        ? "[\(segment.startLine)-\(segment.endLine!)]"
                        : "[\(segment.startLine)]"

                    var text = "\(range) "
                    if let speaker = segment.speaker, !speaker.isEmpty {
                        text += "[\(speaker)] "
                    }
                    text += segment.translationText
                    content += text + "\n\n"
                }
            }
        }

        return content
    }

    // MARK: - PDF Export

    static func generatePdf(
        request: ExportRequest,
        lines: [TextLine]? = nil,
        translations: [TranslationSegment]? = nil
    ) -> Data? {
        let pageWidth: CGFloat = 595  // A4
        let pageHeight: CGFloat = 842
        let margin: CGFloat = 50
        let contentWidth = pageWidth - (margin * 2)
        let lineHeight: CGFloat = 16

        let pdfMetaData = [
            kCGPDFContextCreator: "Classics Viewer" as CFString,
            kCGPDFContextAuthor: request.authorName as CFString,
            kCGPDFContextTitle: "\(request.workTitle) - \(request.bookLabel)" as CFString
        ]

        let format = UIGraphicsPDFRendererFormat()
        format.documentInfo = pdfMetaData as [String: Any]

        let renderer = UIGraphicsPDFRenderer(
            bounds: CGRect(x: 0, y: 0, width: pageWidth, height: pageHeight),
            format: format
        )

        // Use system fonts that support Greek/Latin
        let titleFont = UIFont.systemFont(ofSize: 18, weight: .bold)
        let subtitleFont = UIFont.systemFont(ofSize: 12)
        let bodyFont = UIFont.systemFont(ofSize: 11)

        let titleAttributes: [NSAttributedString.Key: Any] = [
            .font: titleFont,
            .foregroundColor: UIColor.black
        ]

        let subtitleAttributes: [NSAttributedString.Key: Any] = [
            .font: subtitleFont,
            .foregroundColor: UIColor.darkGray
        ]

        let bodyAttributes: [NSAttributedString.Key: Any] = [
            .font: bodyFont,
            .foregroundColor: UIColor.black
        ]

        let data = renderer.pdfData { context in
            var yPosition: CGFloat = margin

            func startNewPage() {
                context.beginPage()
                yPosition = margin
            }

            func ensureSpace(_ needed: CGFloat) {
                if yPosition + needed > pageHeight - margin {
                    startNewPage()
                }
            }

            func drawText(_ text: String, attributes: [NSAttributedString.Key: Any], at point: CGPoint, maxWidth: CGFloat) -> CGFloat {
                let attributedString = NSAttributedString(string: text, attributes: attributes)
                let boundingRect = attributedString.boundingRect(
                    with: CGSize(width: maxWidth, height: .greatestFiniteMagnitude),
                    options: [.usesLineFragmentOrigin, .usesFontLeading],
                    context: nil
                )
                ensureSpace(boundingRect.height)
                attributedString.draw(in: CGRect(x: point.x, y: yPosition, width: maxWidth, height: boundingRect.height))
                return boundingRect.height
            }

            startNewPage()

            // Title
            yPosition += drawText(
                "\(request.authorName) - \(request.workTitle)",
                attributes: titleAttributes,
                at: CGPoint(x: margin, y: yPosition),
                maxWidth: contentWidth
            )
            yPosition += 8

            // Subtitle
            let subtitle = "\(request.bookLabel), Lines \(request.startLine)-\(request.endLine)"
            yPosition += drawText(subtitle, attributes: subtitleAttributes, at: CGPoint(x: margin, y: yPosition), maxWidth: contentWidth)
            yPosition += 4

            if let translator = request.translator {
                yPosition += drawText("Translation by \(translator)", attributes: subtitleAttributes, at: CGPoint(x: margin, y: yPosition), maxWidth: contentWidth)
                yPosition += 4
            }

            yPosition += drawText("Exported from \(request.workId)", attributes: subtitleAttributes, at: CGPoint(x: margin, y: yPosition), maxWidth: contentWidth)
            yPosition += 24

            // Content
            switch request.contentType {
            case .source:
                lines?.forEach { line in
                    let lineNum = String(format: "%5d", line.lineNumber)
                    var text = "\(lineNum)  "
                    if let speaker = line.speaker, !speaker.isEmpty {
                        text += "[\(speaker)] "
                    }
                    text += line.lineText

                    yPosition += drawText(text, attributes: bodyAttributes, at: CGPoint(x: margin, y: yPosition), maxWidth: contentWidth)
                    yPosition += 4
                }

            case .translation:
                translations?.forEach { segment in
                    let range = segment.endLine != nil && segment.endLine != segment.startLine
                        ? "[\(segment.startLine)-\(segment.endLine!)]"
                        : "[\(segment.startLine)]"

                    var text = "\(range) "
                    if let speaker = segment.speaker, !speaker.isEmpty {
                        text += "[\(speaker)] "
                    }
                    text += segment.translationText

                    yPosition += drawText(text, attributes: bodyAttributes, at: CGPoint(x: margin, y: yPosition), maxWidth: contentWidth)
                    yPosition += lineHeight
                }
            }
        }

        return data
    }
}
