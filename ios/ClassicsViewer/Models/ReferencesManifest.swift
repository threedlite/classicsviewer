import Foundation

/// One reference work shipped in the References ODR pack.
/// Mirrors Android `ReferenceEntry` and the on-disk `references_manifest.json`.
struct ReferenceEntry: Codable, Identifiable, Equatable {
    let id: String
    let filename: String
    let title: String
    let author: String
    let language: String
    let pageCount: Int
    let sizeBytes: Int64
}

/// Top-level structure of `references_manifest.json`.
struct ReferencesManifest: Codable, Equatable {
    let version: Int
    let entries: [ReferenceEntry]
}
