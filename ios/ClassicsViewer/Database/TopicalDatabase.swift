import Foundation

/// Single client-side registry: authors.language -> pack base filename.
enum TopicalRegistry {
    static func dbBaseName(_ language: String) -> String? {
        switch language.lowercased() {
        case "greek": return "topical_greek"
        case "latin": return "topical_latin"
        default: return nil
        }
    }

    /// Cheap, synchronous check used for UI affordance visibility.
    static func isPackAvailable(_ language: String) -> Bool {
        guard let base = dbBaseName(language) else { return false }
        return Bundle.main.url(forResource: "\(base).db", withExtension: "zip") != nil
    }
}

/// One related (target) passage: hydrated anchor position + similarity + kind.
struct TopicalTarget {
    let bookId: String
    let lineNumber: Int
    let sequenceNumber: Int
    let similarity: Float
    let kind: String          // "tfidf" or "lda"
    let authorId: String
    let workId: String
}

enum TopicalError: Error {
    case resourceMissing
    case extractFailed(String)
    case malformedPack(String)
    case shaMismatch(String)
}

/// Read-only access to a topical pack built by build_topical_pack.py.
///
/// The pack is six files inside `topical_<language>.db.zip`:
///   positions.bin   sorted-array reverse position lookup
///   rowmeta.bin     per-passage author/work indices + anchor pos + pools
///   T.f16           P x K_topics float16 LDA topic matrix
///   invidx.bin      TF-IDF sparse inverted index
///   vocab.bin       term strings + idf
///   manifest.json   shas + params + kinds_available + kind_labels
///
/// NO SQLite. NO Room. Files are mmap'd; KNN runs at query time. Every failure
/// degrades to "feature unavailable" — the reader never crashes the app and
/// never deletes its own data.
actor TopicalReader {
    private let language: String
    private let packDir: URL
    let manifest: [String: Any]

    private var positions: Data?
    private var rowmeta: Data?
    private var tMatrix: Data?
    private var invidx: Data?
    private var vocab: Data?
    private var ivfCentroids: Data?
    private var ivfLists: Data?
    private var bags: Data?
    private var entityBags: Data?
    private var entityInvidx: Data?
    private var entityVocab: Data?
    private var entityVocabIdfs: [Float] = []
    private var entityTermIndexCache: [String: Int]? = nil

    private var bookIdsCache: [String]?
    private var bookIdToIdxCache: [String: Int]?
    private var authorIdsCache: [String]?
    private var workIdsCache: [String]?
    private var termIndexCache: [String: Int]?

    init?(language: String) {
        guard let base = TopicalRegistry.dbBaseName(language) else { return nil }
        self.language = language
        let fm = FileManager.default
        let support = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        try? fm.createDirectory(at: support, withIntermediateDirectories: true)
        self.packDir = support.appendingPathComponent("topical_unpacked_\(base)")

        do {
            try Self.ensureExtracted(base: base, packDir: packDir)
            let manifestURL = packDir.appendingPathComponent("manifest.json")
            let data = try Data(contentsOf: manifestURL)
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return nil
            }
            self.manifest = json
        } catch {
            return nil
        }
    }

    private static func ensureExtracted(base: String, packDir: URL) throws {
        let fm = FileManager.default
        let manifestURL = packDir.appendingPathComponent("manifest.json")
        let version = (Bundle.main.infoDictionary?["CFBundleVersion"] as? String) ?? "0"
        let versionKey = "topicalPackExtractedVersion_\(base)"
        if fm.fileExists(atPath: manifestURL.path),
           UserDefaults.standard.string(forKey: versionKey) == version {
            return
        }
        try? fm.removeItem(at: packDir)
        try fm.createDirectory(at: packDir, withIntermediateDirectories: true)
        guard let zipURL = Bundle.main.url(forResource: "\(base).db", withExtension: "zip") else {
            throw TopicalError.resourceMissing
        }
        try ZIPHandler.extractAll(from: zipURL, to: packDir)
        UserDefaults.standard.set(version, forKey: versionKey)
    }

    // ----- mmap loaders -----

    private func loadPositions() -> Data? {
        if let p = positions { return p }
        let url = packDir.appendingPathComponent("positions.bin")
        positions = try? Data(contentsOf: url, options: .alwaysMapped)
        return positions
    }
    private func loadRowmeta() -> Data? {
        if let p = rowmeta { return p }
        let url = packDir.appendingPathComponent("rowmeta.bin")
        rowmeta = try? Data(contentsOf: url, options: .alwaysMapped)
        return rowmeta
    }
    private func loadT() -> Data? {
        if let p = tMatrix { return p }
        let url = packDir.appendingPathComponent("T.f16")
        tMatrix = try? Data(contentsOf: url, options: .alwaysMapped)
        return tMatrix
    }
    private func loadInvIdx() -> Data? {
        if let p = invidx { return p }
        let url = packDir.appendingPathComponent("invidx.bin")
        invidx = try? Data(contentsOf: url, options: .alwaysMapped)
        return invidx
    }
    private func loadVocab() -> Data? {
        if let p = vocab { return p }
        let url = packDir.appendingPathComponent("vocab.bin")
        vocab = try? Data(contentsOf: url, options: .alwaysMapped)
        return vocab
    }
    private func loadIvfCentroids() -> Data? {
        if let p = ivfCentroids { return p }
        let url = packDir.appendingPathComponent("ivf.centroids")
        ivfCentroids = try? Data(contentsOf: url, options: .alwaysMapped)
        return ivfCentroids
    }
    private func loadIvfLists() -> Data? {
        if let p = ivfLists { return p }
        let url = packDir.appendingPathComponent("ivf.lists")
        ivfLists = try? Data(contentsOf: url, options: .alwaysMapped)
        return ivfLists
    }
    private func loadBags() -> Data? {
        if let p = bags { return p }
        let url = packDir.appendingPathComponent("bags.bin")
        bags = try? Data(contentsOf: url, options: .alwaysMapped)
        return bags
    }
    private func loadEntityBags() -> Data? {
        if let p = entityBags { return p }
        let url = packDir.appendingPathComponent("entity_bags.bin")
        entityBags = try? Data(contentsOf: url, options: .alwaysMapped)
        return entityBags
    }
    private func loadEntityInvIdx() -> Data? {
        if let p = entityInvidx { return p }
        let url = packDir.appendingPathComponent("entity_invidx.bin")
        entityInvidx = try? Data(contentsOf: url, options: .alwaysMapped)
        return entityInvidx
    }
    private func loadEntityVocab() -> Data? {
        if let p = entityVocab { return p }
        let url = packDir.appendingPathComponent("entity_vocab.bin")
        entityVocab = try? Data(contentsOf: url, options: .alwaysMapped)
        return entityVocab
    }

    private func ensureEntityTermIndex() {
        if entityTermIndexCache != nil { return }
        guard let v = loadEntityVocab() else { return }
        guard u32(v, 0) == 0x564F4331 else { return }
        let n = Int(u32(v, 8))
        let fileSize = v.count
        let offArrStart = fileSize - (n + 1) * 4
        var map = [String: Int](minimumCapacity: n)
        var idfs = [Float](repeating: 0, count: n)
        for i in 0..<n {
            let off = Int(u32(v, offArrStart + i * 4))
            let len = Int(u16(v, off))
            let term = String(data: v.subdata(in: (off + 2)..<(off + 2 + len)),
                              encoding: .utf8) ?? ""
            let idfH = u16(v, off + 2 + len)
            idfs[i] = halfToFloat(idfH)
            map[term] = i
        }
        entityTermIndexCache = map
        entityVocabIdfs = idfs
    }

    /// Pre-built (term_idx -> tf) PROPN bag for source row from entity_bags.bin.
    func entitySourceBag(rowIdx: Int) -> [Int: Int] {
        guard let b = loadEntityBags(), rowIdx >= 0, rowIdx < passageCount else { return [:] }
        guard u32(b, 0) == 0x42414731 else { return [:] }
        let recordCount = Int(u32(b, 8))
        if rowIdx >= recordCount { return [:] }
        let entriesOffset = Int(u32(b, 12))
        let rowOffsetsBase = 16
        let startIdx = Int(u32(b, rowOffsetsBase + rowIdx * 4))
        let endIdx = Int(u32(b, rowOffsetsBase + (rowIdx + 1) * 4))
        var out = [Int: Int]()
        out.reserveCapacity(endIdx - startIdx)
        var off = entriesOffset + startIdx * 6
        for _ in startIdx..<endIdx {
            out[Int(u32(b, off))] = Int(u16(b, off + 4))
            off += 6
        }
        return out
    }

    func entityKnn(srcRowIdx: Int, queryTf: [Int: Int], K: Int, minSim: Float) -> [Hit] {
        ensureEntityTermIndex()
        ensureNamePools()
        guard srcRowIdx >= 0 && srcRowIdx < passageCount, !queryTf.isEmpty,
              let iv = loadEntityInvIdx() else { return [] }
        guard u32(iv, 0) == 0x494E5631 else { return [] }
        let postingsOffset = Int(u32(iv, 12))
        let src = rowMeta(srcRowIdx)

        var qWeights = [Int: Float]()
        var nrm: Double = 0
        for (idx, c) in queryTf {
            guard idx < entityVocabIdfs.count else { continue }
            let w = (1.0 + log(Double(c))) * Double(entityVocabIdfs[idx])
            qWeights[idx] = Float(w)
            nrm += w * w
        }
        let scale = Float(sqrt(nrm))
        if scale == 0 { return [] }
        for k in qWeights.keys { qWeights[k] = qWeights[k]! / scale }

        var sims = [Int: Float]()
        for (termIdx, qw) in qWeights {
            let base = 16 + termIdx * 4
            let start = postingsOffset + Int(u32(iv, base))
            let end = postingsOffset + Int(u32(iv, base + 4))
            iv.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                let basePtr = raw.baseAddress!
                var off = start
                while off < end {
                    let rowIdx = Int(basePtr.advanced(by: off).load(as: UInt32.self))
                    let docH = basePtr.advanced(by: off + 4).load(as: UInt16.self)
                    off += 6
                    if rowIdx == srcRowIdx { continue }
                    let docW = halfToFloat(docH)
                    sims[rowIdx, default: 0] += qw * docW
                }
            }
        }
        if sims.isEmpty { return [] }
        var heap = TopKHeap(K: K)
        for (rowIdx, s) in sims {
            if s <= minSim { continue }
            let m = rowMeta(rowIdx)
            if m.workIdx == src.workIdx { continue }
            heap.offer(rowIdx: rowIdx, sim: s)
        }
        return heap.sortedDescending()
    }

    /// Pre-built (term_idx -> tf) source-passage bag, read from bags.bin.
    /// Empty if bags.bin isn't shipped or row out of range.
    func sourceBag(rowIdx: Int) -> [Int: Int] {
        guard let b = loadBags(), rowIdx >= 0, rowIdx < passageCount else { return [:] }
        guard u32(b, 0) == 0x42414731 else { return [:] }
        let recordCount = Int(u32(b, 8))
        if rowIdx >= recordCount { return [:] }
        let entriesOffset = Int(u32(b, 12))
        let rowOffsetsBase = 16
        let startIdx = Int(u32(b, rowOffsetsBase + rowIdx * 4))
        let endIdx = Int(u32(b, rowOffsetsBase + (rowIdx + 1) * 4))
        var out = [Int: Int]()
        out.reserveCapacity(endIdx - startIdx)
        var off = entriesOffset + startIdx * 6
        for _ in startIdx..<endIdx {
            let termIdx = Int(u32(b, off))
            let tf = Int(u16(b, off + 4))
            out[termIdx] = tf
            off += 6
        }
        return out
    }

    // ----- positions.bin parser -----

    private func u32(_ d: Data, _ offset: Int) -> UInt32 {
        d.subdata(in: offset..<(offset + 4)).withUnsafeBytes { $0.load(as: UInt32.self) }
    }
    private func i32(_ d: Data, _ offset: Int) -> Int32 {
        d.subdata(in: offset..<(offset + 4)).withUnsafeBytes { $0.load(as: Int32.self) }
    }
    private func u16(_ d: Data, _ offset: Int) -> UInt16 {
        d.subdata(in: offset..<(offset + 2)).withUnsafeBytes { $0.load(as: UInt16.self) }
    }

    private func ensureBookIds() {
        if bookIdsCache != nil { return }
        guard let p = loadPositions() else { return }
        let poolOffset = Int(u32(p, 16))
        let count = Int(u32(p, poolOffset))
        var ids = [String]()
        ids.reserveCapacity(count)
        var cursor = poolOffset + 4
        for _ in 0..<count {
            let len = Int(u16(p, cursor)); cursor += 2
            let s = String(data: p.subdata(in: cursor..<(cursor + len)), encoding: .utf8) ?? ""
            ids.append(s)
            cursor += len
        }
        bookIdsCache = ids
        var map = [String: Int](minimumCapacity: count)
        for (i, s) in ids.enumerated() { map[s] = i }
        bookIdToIdxCache = map
    }

    /// Look up (bookId, line, seq) -> row_idx. Tries exact match first; falls
    /// back to any row matching (bookId, line) so callers whose
    /// sequence_number disagrees with text_lines still resolve. Same passage.
    func lookupRow(bookId: String, lineNumber: Int, sequenceNumber: Int) -> Int {
        ensureBookIds()
        guard let p = loadPositions() else { return -1 }
        guard let bidx = bookIdToIdxCache?[bookId] else { return -1 }
        let recordCount = Int(u32(p, 8))
        let stride = Int(u32(p, 12))

        // 1) exact match
        do {
            var lo = 0
            var hi = recordCount - 1
            while lo <= hi {
                let mid = (lo + hi) / 2
                let off = 32 + mid * stride
                let midBidx = Int(u32(p, off))
                let midLine = Int(i32(p, off + 4))
                let midSeq = Int(i32(p, off + 8))
                let cmp: Int
                if midBidx != bidx { cmp = midBidx - bidx }
                else if midLine != lineNumber { cmp = midLine - lineNumber }
                else { cmp = midSeq - sequenceNumber }
                if cmp == 0 { return Int(i32(p, off + 12)) }
                if cmp < 0 { lo = mid + 1 } else { hi = mid - 1 }
            }
        }

        // 2) fallback by (bidx, line)
        var lo = 0
        var hi = recordCount - 1
        while lo <= hi {
            let mid = (lo + hi) / 2
            let off = 32 + mid * stride
            let midBidx = Int(u32(p, off))
            let midLine = Int(i32(p, off + 4))
            let cmp: Int
            if midBidx != bidx { cmp = midBidx - bidx }
            else { cmp = midLine - lineNumber }
            if cmp == 0 {
                var i = mid
                while i > 0 {
                    let o = 32 + (i - 1) * stride
                    if Int(u32(p, o)) == bidx && Int(i32(p, o + 4)) == lineNumber {
                        i -= 1
                    } else { break }
                }
                let firstOff = 32 + i * stride
                return Int(i32(p, firstOff + 12))
            }
            if cmp < 0 { lo = mid + 1 } else { hi = mid - 1 }
        }
        return -1
    }

    // ----- rowmeta.bin parser -----

    private struct RowMeta {
        let authorIdx: Int
        let workIdx: Int
        let anchorBookIdIdx: Int
        let anchorLine: Int
        let anchorSeq: Int
    }

    private func rowMeta(_ rowIdx: Int) -> RowMeta {
        guard let r = loadRowmeta() else {
            return RowMeta(authorIdx: 0, workIdx: 0, anchorBookIdIdx: 0,
                           anchorLine: 0, anchorSeq: 0)
        }
        let off = 16 + rowIdx * 20
        return RowMeta(
            authorIdx: Int(u32(r, off)),
            workIdx: Int(u32(r, off + 4)),
            anchorBookIdIdx: Int(u32(r, off + 8)),
            anchorLine: Int(i32(r, off + 12)),
            anchorSeq: Int(i32(r, off + 16))
        )
    }

    private func ensureNamePools() {
        if authorIdsCache != nil { return }
        guard let r = loadRowmeta() else { return }
        let fileSize = r.count
        let authorOff = Int(u32(r, fileSize - 16))
        let workOff = Int(u32(r, fileSize - 12))
        authorIdsCache = readStringPool(r, authorOff)
        workIdsCache = readStringPool(r, workOff)
    }

    private func readStringPool(_ d: Data, _ offset: Int) -> [String] {
        let count = Int(u32(d, offset))
        var out = [String](); out.reserveCapacity(count)
        var cur = offset + 4
        for _ in 0..<count {
            let len = Int(u16(d, cur)); cur += 2
            let s = String(data: d.subdata(in: cur..<(cur + len)), encoding: .utf8) ?? ""
            out.append(s); cur += len
        }
        return out
    }

    // ----- T.f16 reading -----

    private var passageCount: Int {
        (manifest["passage_count"] as? NSNumber)?.intValue ?? 0
    }
    private var ldaDim: Int {
        (manifest["lda_topics"] as? NSNumber)?.intValue ?? 0
    }

    private func readTRow(_ rowIdx: Int) -> [Float] {
        let K = ldaDim
        guard let t = loadT() else { return [] }
        var out = [Float](repeating: 0, count: K)
        let off = rowIdx * K * 2
        out.withUnsafeMutableBufferPointer { buf in
            t.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                let base = raw.baseAddress!.advanced(by: off).assumingMemoryBound(to: UInt16.self)
                for k in 0..<K { buf[k] = halfToFloat(base[k]) }
            }
        }
        return out
    }

    private nonisolated func halfToFloat(_ h: UInt16) -> Float {
        let sign = (h >> 15) & 0x1
        let exp  = (h >> 10) & 0x1F
        let frac = h & 0x3FF
        let bits: UInt32
        if exp == 0 {
            if frac == 0 {
                bits = UInt32(sign) << 31
            } else {
                var e: Int32 = -1
                var f0 = UInt32(frac)
                repeat { e += 1; f0 <<= 1 } while (f0 & 0x400) == 0
                bits = (UInt32(sign) << 31) |
                    UInt32(Int32(127 - 15) - e) << 23 |
                    ((f0 & 0x3FF) << 13)
            }
        } else if exp == 0x1F {
            bits = (UInt32(sign) << 31) | (0xFF << 23) | (UInt32(frac) << 13)
        } else {
            bits = (UInt32(sign) << 31) |
                ((UInt32(exp) + UInt32(127 - 15)) << 23) |
                (UInt32(frac) << 13)
        }
        return Float(bitPattern: bits)
    }

    // ----- vocab.bin parser -----

    private var vocabSize: Int {
        (manifest["vocab_size"] as? NSNumber)?.intValue ?? 0
    }

    private func ensureTermIndex() {
        if termIndexCache != nil { return }
        guard let v = loadVocab() else { return }
        let n = vocabSize
        let fileSize = v.count
        let offArrStart = fileSize - (n + 1) * 4
        var map = [String: Int](minimumCapacity: n)
        var idfs = [Float](repeating: 0, count: n)
        for i in 0..<n {
            let off = Int(u32(v, offArrStart + i * 4))
            let len = Int(u16(v, off))
            let term = String(data: v.subdata(in: (off + 2)..<(off + 2 + len)),
                              encoding: .utf8) ?? ""
            let idfH = u16(v, off + 2 + len)
            idfs[i] = halfToFloat(idfH)
            map[term] = i
        }
        termIndexCache = map
        vocabIdfs = idfs
    }
    private var vocabIdfs: [Float] = []

    // ----- invidx.bin parser -----

    private struct InvHeader {
        let postingsOffset: Int
        let vocabSize: Int
    }

    private func invHeader() -> InvHeader? {
        guard let iv = loadInvIdx() else { return nil }
        return InvHeader(
            postingsOffset: Int(u32(iv, 12)),
            vocabSize: Int(u32(iv, 8)),
        )
    }

    private func invPostingsRange(_ termIdx: Int) -> (start: Int, end: Int)? {
        guard let h = invHeader(), let iv = loadInvIdx() else { return nil }
        let base = 16 + termIdx * 4
        let start = Int(u32(iv, base))
        let end = Int(u32(iv, base + 4))
        return (h.postingsOffset + start, h.postingsOffset + end)
    }

    // ----- KNN -----

    struct Hit {
        let rowIdx: Int
        let similarity: Float
    }

    func ldaKnn(srcRowIdx: Int, K: Int, minSim: Float, nprobe: Int = 10) -> [Hit] {
        ensureNamePools()
        guard srcRowIdx >= 0 && srcRowIdx < passageCount,
              let t = loadT(),
              let centroids = loadIvfCentroids(),
              let lists = loadIvfLists() else {
            // No brute-force fallback — fail closed when IVF isn't shipped.
            return []
        }
        // ivf.lists header: magic, version, nlist, offsetsOffset
        guard u32(lists, 0) == 0x49564631 else { return [] }
        let nlist = Int(u32(lists, 8))
        let offsetsOffset = Int(u32(lists, 12))
        let q = readTRow(srcRowIdx)
        let src = rowMeta(srcRowIdx)
        let Kdim = ldaDim

        // 1) score q against every centroid
        var centroidSims = [Float](repeating: 0, count: nlist)
        centroids.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
            let base = raw.baseAddress!.assumingMemoryBound(to: UInt16.self)
            for c in 0..<nlist {
                let off = c * Kdim
                var sum: Float = 0
                for k in 0..<Kdim {
                    sum += halfToFloat(base[off + k]) * q[k]
                }
                centroidSims[c] = sum
            }
        }

        // 2) pick top nprobe centroids
        let nprobeEff = min(nprobe, nlist)
        var cTop = TopKHeap(K: nprobeEff)
        for c in 0..<nlist { cTop.offer(rowIdx: c, sim: centroidSims[c]) }
        let pickedCentroids = cTop.sortedDescending().map { $0.rowIdx }

        // 3) score only rows in those centroids' lists
        var heap = TopKHeap(K: K)
        let rowsBase = offsetsOffset + (nlist + 1) * 4
        t.withUnsafeBytes { (rawT: UnsafeRawBufferPointer) in
            let tBase = rawT.baseAddress!.assumingMemoryBound(to: UInt16.self)
            lists.withUnsafeBytes { (rawL: UnsafeRawBufferPointer) in
                let lBaseU8 = rawL.baseAddress!
                for c in pickedCentroids {
                    let startIdx = Int(u32(lists, offsetsOffset + c * 4))
                    let endIdx = Int(u32(lists, offsetsOffset + (c + 1) * 4))
                    var off = rowsBase + startIdx * 4
                    let end = rowsBase + endIdx * 4
                    while off < end {
                        let i = Int(lBaseU8.advanced(by: off).load(as: UInt32.self))
                        off += 4
                        if i == srcRowIdx { continue }
                        let m = rowMeta(i)
                        if m.workIdx == src.workIdx { continue }
                        let rowOff = i * Kdim
                        var sum: Float = 0
                        for k in 0..<Kdim {
                            sum += halfToFloat(tBase[rowOff + k]) * q[k]
                        }
                        if sum > minSim { heap.offer(rowIdx: i, sim: sum) }
                    }
                }
            }
        }
        return heap.sortedDescending()
    }

    func tfidfKnn(srcRowIdx: Int, queryTf: [Int: Int], K: Int, minSim: Float) -> [Hit] {
        ensureTermIndex()
        ensureNamePools()
        guard srcRowIdx >= 0 && srcRowIdx < passageCount, !queryTf.isEmpty,
              let iv = loadInvIdx() else { return [] }
        let src = rowMeta(srcRowIdx)
        let tf = queryTf
        var qWeights = [Int: Float]()
        var nrm: Double = 0
        for (idx, c) in tf {
            let w = (1.0 + log(Double(c))) * Double(vocabIdfs[idx])
            qWeights[idx] = Float(w)
            nrm += w * w
        }
        let scale = Float(sqrt(nrm))
        if scale == 0 { return [] }
        for k in qWeights.keys { qWeights[k] = qWeights[k]! / scale }

        var sims = [Int: Float]()
        for (termIdx, qw) in qWeights {
            guard let range = invPostingsRange(termIdx) else { continue }
            iv.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
                let base = raw.baseAddress!
                var off = range.start
                while off < range.end {
                    let rowIdx = Int(base.advanced(by: off).load(as: UInt32.self))
                    let docH = base.advanced(by: off + 4).load(as: UInt16.self)
                    off += 6
                    if rowIdx == srcRowIdx { continue }
                    let docW = halfToFloat(docH)
                    sims[rowIdx, default: 0] += qw * docW
                }
            }
        }
        if sims.isEmpty { return [] }
        var heap = TopKHeap(K: K)
        for (rowIdx, s) in sims {
            if s <= minSim { continue }
            let m = rowMeta(rowIdx)
            if m.workIdx == src.workIdx { continue }
            heap.offer(rowIdx: rowIdx, sim: s)
        }
        return heap.sortedDescending()
    }

    private struct TopKHeap {
        let K: Int
        var rows: [Int]
        var sims: [Float]
        var n: Int = 0
        init(K: Int) {
            self.K = K
            self.rows = [Int](repeating: 0, count: K)
            self.sims = [Float](repeating: 0, count: K)
        }
        mutating func offer(rowIdx: Int, sim: Float) {
            if n < K {
                rows[n] = rowIdx; sims[n] = sim; n += 1
                if n == K { heapify() }
                return
            }
            if sim <= sims[0] { return }
            rows[0] = rowIdx; sims[0] = sim
            siftDown(0)
        }
        mutating func heapify() {
            for i in stride(from: (K / 2 - 1), through: 0, by: -1) { siftDown(i) }
        }
        mutating func siftDown(_ start: Int) {
            var i = start
            while true {
                let l = 2 * i + 1; let r = l + 1
                var m = i
                if l < n && sims[l] < sims[m] { m = l }
                if r < n && sims[r] < sims[m] { m = r }
                if m == i { return }
                rows.swapAt(i, m); sims.swapAt(i, m)
                i = m
            }
        }
        func sortedDescending() -> [Hit] {
            (0..<n).map { Hit(rowIdx: rows[$0], similarity: sims[$0]) }
                .sorted { $0.similarity > $1.similarity }
        }
    }

    // ----- hit hydration -----

    func hydrate(_ hit: Hit, kind: String) -> TopicalTarget? {
        ensureBookIds()
        ensureNamePools()
        guard let bookIds = bookIdsCache, let authors = authorIdsCache,
              let works = workIdsCache else { return nil }
        let m = rowMeta(hit.rowIdx)
        guard m.anchorBookIdIdx < bookIds.count,
              m.authorIdx < authors.count, m.workIdx < works.count else { return nil }
        return TopicalTarget(
            bookId: bookIds[m.anchorBookIdIdx],
            lineNumber: m.anchorLine,
            sequenceNumber: m.anchorSeq,
            similarity: hit.similarity,
            kind: kind,
            authorId: authors[m.authorIdx],
            workId: works[m.workIdx]
        )
    }

    // ----- manifest accessors -----

    var kindsAvailable: [String] {
        (manifest["kinds_available"] as? [String]) ?? []
    }
    var defaultKind: String {
        (manifest["default_kind"] as? String) ?? "lda"
    }
    var ldaMinSim: Float {
        Float((manifest["lda_min_sim"] as? NSNumber)?.doubleValue ?? 0.5)
    }
    var tfidfMinSim: Float {
        Float((manifest["tfidf_min_sim"] as? NSNumber)?.doubleValue ?? 0.15)
    }
    var entityMinSim: Float {
        Float((manifest["entity_min_sim"] as? NSNumber)?.doubleValue ?? 0.20)
    }
    func kindUiLabel(_ kind: String) -> String {
        guard let labels = manifest["kind_labels"] as? [String: Any],
              let entry = labels[kind] as? [String: Any],
              let ui = entry["ui"] as? String else { return kind }
        return ui
    }
    func kindUiHint(_ kind: String) -> String {
        guard let labels = manifest["kind_labels"] as? [String: Any],
              let entry = labels[kind] as? [String: Any],
              let hint = entry["hint"] as? String else { return "" }
        return hint
    }
}
