package com.classicsviewer.app.topical

import android.content.Context
import android.util.Log
import com.classicsviewer.app.BuildConfig
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.util.zip.ZipInputStream
import kotlin.math.min

/**
 * Read-only access to a topical pack (positions.bin / rowmeta.bin / T.f16 /
 * invidx.bin / vocab.bin / manifest.json) extracted from `topical_<lang>.db.zip`.
 *
 * No SQLite, no Room. Files are mmap'd; KNN is computed at query time. Every
 * failure degrades to "feature unavailable" — the helper never crashes the app
 * and never deletes its own data.
 *
 * The on-disk format is documented in topical/TOPICAL.md Part 1 §2.
 */
class TopicalReader private constructor(
    private val context: Context,
    private val language: String,
    private val packDir: File,
    val manifest: JSONObject,
) {

    companion object {
        private const val TAG = "TopicalReader"
        private const val KEY_BUILD_ID = "topical_build_id"
        private const val PACK_FILE_NAMES = "positions.bin,rowmeta.bin,T.f16,invidx.bin,vocab.bin,manifest.json"

        /** Open the pack for `language`, extracting on first use. Returns null if
         *  the pack is not installed or any file is missing / mismatched. */
        fun open(context: Context, language: String): TopicalReader? {
            return try {
                val stem = stemFor(language) ?: return null
                val packDir = File(context.cacheDir, "topical_unpacked_$stem").apply { mkdirs() }
                val prefsName = "topical_reader_$stem"
                val prefs = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)

                val manifestFile = File(packDir, "manifest.json")
                val needExtract = !manifestFile.exists() ||
                    prefs.getInt("apk_version_code", -1) != BuildConfig.VERSION_CODE

                if (needExtract) {
                    wipeAll(packDir)
                    if (!extractFromAssetPack(context, stem, packDir)) {
                        Log.w(TAG, "extraction failed for $language pack")
                        return null
                    }
                    prefs.edit().putInt("apk_version_code", BuildConfig.VERSION_CODE).apply()
                }

                val manifest = JSONObject(manifestFile.readText())
                val files = manifest.getJSONObject("files")
                val it = files.keys()
                while (it.hasNext()) {
                    val name = it.next()
                    val expected = files.getJSONObject(name).getString("sha256")
                    val actual = sha256File(File(packDir, name))
                    if (actual != expected) {
                        Log.w(TAG, "sha mismatch on $name (expected $expected got $actual); will retry once")
                        wipeAll(packDir)
                        if (!extractFromAssetPack(context, stem, packDir)) return null
                        val again = sha256File(File(packDir, name))
                        if (again != expected) {
                            Log.w(TAG, "sha still mismatched on $name after re-extract; pack unusable")
                            return null
                        }
                    }
                }

                TopicalReader(context, language, packDir, manifest)
            } catch (e: Exception) {
                Log.w(TAG, "open failed", e)
                null
            }
        }

        fun isSupported(language: String?): Boolean = stemFor(language) != null

        /** Fast synchronous "is the pack zip present so the icon can show?"
         *  check. Side-effect-free: does NOT seed the debug cache (which would
         *  copy ~500 MB of zips out of APK assets and delay icon visibility).
         *  Extraction and sha verification still happen at click time via
         *  [open]. */
        fun isPackInstalled(context: Context, language: String): Boolean {
            val stem = stemFor(language) ?: return false
            return try {
                TopicalPackManager(context).hasPackZip(stem)
            } catch (e: Exception) {
                false
            }
        }

        private fun stemFor(language: String?): String? = when (language?.lowercase()) {
            "greek" -> "topical_greek"
            "latin" -> "topical_latin"
            else -> null
        }

        private fun wipeAll(dir: File) {
            dir.listFiles()?.forEach { runCatching { it.delete() } }
        }

        /** Copy the per-language zip out of the asset pack (or debug assets) and
         *  unzip its entries into `packDir`. */
        private fun extractFromAssetPack(context: Context, stem: String, packDir: File): Boolean {
            val packAssets = TopicalPackManager(context).getAssetsPath() ?: return false
            val zipFile = File(packAssets, "$stem.db.zip")
            if (!zipFile.exists()) {
                Log.w(TAG, "$zipFile not found in asset pack")
                return false
            }
            return try {
                zipFile.inputStream().buffered().use { input ->
                    ZipInputStream(input).use { zis ->
                        var entry = zis.nextEntry
                        while (entry != null) {
                            if (!entry.isDirectory) {
                                val out = File(packDir, entry.name)
                                out.outputStream().buffered().use { os -> zis.copyTo(os) }
                            }
                            entry = zis.nextEntry
                        }
                    }
                }
                true
            } catch (e: Exception) {
                Log.w(TAG, "unzip failed", e)
                false
            }
        }

        private fun sha256File(f: File): String {
            val md = java.security.MessageDigest.getInstance("SHA-256")
            f.inputStream().buffered().use { ins ->
                val buf = ByteArray(1 shl 20)
                while (true) {
                    val n = ins.read(buf); if (n < 0) break; md.update(buf, 0, n)
                }
            }
            return md.digest().joinToString("") { "%02x".format(it) }
        }
    }

    // ----- mmap'd files (lazy) -----

    private val positionsFile = File(packDir, "positions.bin")
    private val rowmetaFile = File(packDir, "rowmeta.bin")
    private val tFile = File(packDir, "T.f16")
    private val invidxFile = File(packDir, "invidx.bin")
    private val vocabFile = File(packDir, "vocab.bin")

    private val ivfCentroidsFile = File(packDir, "ivf.centroids")
    private val ivfListsFile = File(packDir, "ivf.lists")
    private val bagsFile = File(packDir, "bags.bin")
    private val entityBagsFile = File(packDir, "entity_bags.bin")
    private val entityInvidxFile = File(packDir, "entity_invidx.bin")
    private val entityVocabFile = File(packDir, "entity_vocab.bin")

    private val posBuf: ByteBuffer by lazy { mmap(positionsFile) }
    private val rmBuf: ByteBuffer by lazy { mmap(rowmetaFile) }
    private val tBuf: ByteBuffer by lazy { mmap(tFile) }
    private val invBuf: ByteBuffer by lazy { mmap(invidxFile) }
    private val vocBuf: ByteBuffer by lazy { mmap(vocabFile) }
    private val centroidsBuf: ByteBuffer? by lazy {
        if (ivfCentroidsFile.exists()) mmap(ivfCentroidsFile) else null
    }
    private val listsBuf: ByteBuffer? by lazy {
        if (ivfListsFile.exists()) mmap(ivfListsFile) else null
    }
    private val bagsBuf: ByteBuffer? by lazy {
        if (bagsFile.exists()) mmap(bagsFile) else null
    }
    private val entityBagsBuf: ByteBuffer? by lazy {
        if (entityBagsFile.exists()) mmap(entityBagsFile) else null
    }
    private val entityInvBuf: ByteBuffer? by lazy {
        if (entityInvidxFile.exists()) mmap(entityInvidxFile) else null
    }
    private val entityVocBuf: ByteBuffer? by lazy {
        if (entityVocabFile.exists()) mmap(entityVocabFile) else null
    }

    private fun mmap(f: File): ByteBuffer =
        RandomAccessFile(f, "r").use { raf ->
            raf.channel.map(FileChannel.MapMode.READ_ONLY, 0, f.length())
                .order(ByteOrder.LITTLE_ENDIAN)
        }

    // ----- positions.bin parser -----

    private data class PositionsHeader(
        val recordCount: Int, val recStride: Int,
        val poolOffset: Int, val poolBytes: Int, val bookIdCount: Int,
    )

    private val posHeader: PositionsHeader by lazy {
        val b = posBuf
        val magic = b.getInt(0)
        require(magic == 0x504F5331) { "positions.bin bad magic" }
        PositionsHeader(
            recordCount = b.getInt(8),
            recStride = b.getInt(12),
            poolOffset = b.getInt(16),
            poolBytes = b.getInt(20),
            bookIdCount = b.getInt(24),
        )
    }

    /** Cached `book_id_idx → book_id (String)` materialised once. */
    private val bookIds: Array<String> by lazy {
        val h = posHeader
        val pool = posBuf.duplicate().apply { order(ByteOrder.LITTLE_ENDIAN); position(h.poolOffset) }
        val count = pool.int  // u32
        val out = Array(count) { "" }
        for (i in 0 until count) {
            val len = pool.short.toInt() and 0xFFFF
            val buf = ByteArray(len)
            pool.get(buf)
            out[i] = String(buf, Charsets.UTF_8)
        }
        out
    }

    /** Reverse map: book_id → book_id_idx, materialised on first use. */
    private val bookIdToIdx: Map<String, Int> by lazy {
        val map = HashMap<String, Int>(bookIds.size * 2)
        bookIds.forEachIndexed { i, s -> map[s] = i }
        map
    }

    /** Look up `(book_id, line, seq) → row_idx`. Tries exact match first; falls
     *  back to ANY row for `(book_id, line)` (different `sequence_number`s in
     *  the same line all belong to the same passage anyway, so the fallback
     *  resolves callers whose seq-numbering disagrees with text_lines.). */
    fun lookupRow(bookId: String, line: Int, seq: Int): Int {
        val bidx = bookIdToIdx[bookId] ?: return -1
        val h = posHeader
        val stride = h.recStride

        // 1) exact match
        run {
            var lo = 0; var hi = h.recordCount - 1
            while (lo <= hi) {
                val mid = (lo + hi) ushr 1
                val off = 32 + mid * stride
                val midBidx = posBuf.getInt(off)
                val midLine = posBuf.getInt(off + 4)
                val midSeq = posBuf.getInt(off + 8)
                val cmp = when {
                    midBidx != bidx -> midBidx - bidx
                    midLine != line -> midLine - line
                    else -> midSeq - seq
                }
                when {
                    cmp == 0 -> return posBuf.getInt(off + 12)
                    cmp < 0 -> lo = mid + 1
                    else -> hi = mid - 1
                }
            }
        }

        // 2) fallback: find lowest index with (bidx, line); accept any seq
        var lo = 0; var hi = h.recordCount - 1
        while (lo <= hi) {
            val mid = (lo + hi) ushr 1
            val off = 32 + mid * stride
            val midBidx = posBuf.getInt(off)
            val midLine = posBuf.getInt(off + 4)
            val cmp = when {
                midBidx != bidx -> midBidx - bidx
                else -> midLine - line
            }
            when {
                cmp == 0 -> {
                    // walk back to the FIRST row with (bidx, line)
                    var i = mid
                    while (i > 0) {
                        val o = 32 + (i - 1) * stride
                        if (posBuf.getInt(o) == bidx && posBuf.getInt(o + 4) == line) i-- else break
                    }
                    val firstOff = 32 + i * stride
                    return posBuf.getInt(firstOff + 12)
                }
                cmp < 0 -> lo = mid + 1
                else -> hi = mid - 1
            }
        }
        return -1
    }

    // ----- rowmeta.bin parser -----

    private data class RowMeta(
        val authorIdx: Int, val workIdx: Int,
        val anchorBookIdIdx: Int, val anchorLine: Int, val anchorSeq: Int,
    )

    private val rmHeader = Triple(
        16,            // header size
        20,            // stride
        0,             // recordCount filled in lazily
    )

    private val rmRecordCount: Int by lazy {
        require(rmBuf.getInt(0) == 0x524F4D31) { "rowmeta.bin bad magic" }
        rmBuf.getInt(8)
    }

    private fun rowMeta(rowIdx: Int): RowMeta {
        val off = 16 + rowIdx * 20
        return RowMeta(
            authorIdx = rmBuf.getInt(off),
            workIdx = rmBuf.getInt(off + 4),
            anchorBookIdIdx = rmBuf.getInt(off + 8),
            anchorLine = rmBuf.getInt(off + 12),
            anchorSeq = rmBuf.getInt(off + 16),
        )
    }

    private val authorIds: Array<String> by lazy {
        // After records, footer is at file end (16 bytes): author_off, work_off, book_off, marker
        val fileSize = rmBuf.capacity()
        val authorOff = rmBuf.getInt(fileSize - 16)
        readStringPool(rmBuf, authorOff)
    }

    private val workIds: Array<String> by lazy {
        val fileSize = rmBuf.capacity()
        val workOff = rmBuf.getInt(fileSize - 12)
        readStringPool(rmBuf, workOff)
    }

    private fun readStringPool(buf: ByteBuffer, offset: Int): Array<String> {
        val dup = buf.duplicate().apply { order(ByteOrder.LITTLE_ENDIAN); position(offset) }
        val count = dup.int
        val out = Array(count) { "" }
        for (i in 0 until count) {
            val len = dup.short.toInt() and 0xFFFF
            val b = ByteArray(len); dup.get(b)
            out[i] = String(b, Charsets.UTF_8)
        }
        return out
    }

    // ----- T.f16 -----

    private val passageCount: Int by lazy { manifest.getInt("passage_count") }
    private val ldaDim: Int by lazy { manifest.getInt("lda_topics") }

    /** Read a single row of T as a float32 array (decoded from f16). */
    private fun readTRow(rowIdx: Int): FloatArray {
        val K = ldaDim
        val out = FloatArray(K)
        val off = rowIdx * K * 2
        for (k in 0 until K) {
            val h = tBuf.getShort(off + k * 2).toInt() and 0xFFFF
            out[k] = halfToFloat(h)
        }
        return out
    }

    /** IEEE 754 half-precision → float32. */
    private fun halfToFloat(h: Int): Float {
        val sign = (h ushr 15) and 0x1
        val exp = (h ushr 10) and 0x1F
        val frac = h and 0x3FF
        val f: Int = when (exp) {
            0 -> {
                if (frac == 0) sign shl 31
                else {
                    var e = -1
                    var f0 = frac
                    do { e++; f0 = f0 shl 1 } while ((f0 and 0x400) == 0)
                    val bits = (sign shl 31) or ((127 - 15 - e) shl 23) or ((f0 and 0x3FF) shl 13)
                    bits
                }
            }
            0x1F -> (sign shl 31) or (0xFF shl 23) or (frac shl 13)
            else -> (sign shl 31) or ((exp + (127 - 15)) shl 23) or (frac shl 13)
        }
        return Float.fromBits(f)
    }

    // ----- vocab.bin parser -----

    private data class VocabEntry(val term: String, val idf: Float)

    private val vocabSize: Int by lazy {
        require(vocBuf.getInt(0) == 0x564F4331) { "vocab.bin bad magic" }
        vocBuf.getInt(8)
    }

    private val vocabOffsets: IntArray by lazy {
        val n = vocabSize
        // body sits between header (12 bytes) and final offsets array (n+1 u32).
        val fileSize = vocBuf.capacity()
        val offArrayStart = fileSize - (n + 1) * 4
        val arr = IntArray(n + 1)
        for (i in 0..n) arr[i] = vocBuf.getInt(offArrayStart + i * 4)
        arr
    }

    private fun vocabEntry(idx: Int): VocabEntry {
        val off = vocabOffsets[idx]
        val len = vocBuf.getShort(off).toInt() and 0xFFFF
        val b = ByteArray(len)
        val dup = vocBuf.duplicate(); dup.position(off + 2); dup.get(b)
        val term = String(b, Charsets.UTF_8)
        val idfH = vocBuf.getShort(off + 2 + len).toInt() and 0xFFFF
        return VocabEntry(term, halfToFloat(idfH))
    }

    /** Cached `term → vocab_idx` map for query construction. */
    private val termIndex: Map<String, Int> by lazy {
        val m = HashMap<String, Int>(vocabSize * 2)
        for (i in 0 until vocabSize) m[vocabEntry(i).term] = i
        m
    }

    // ----- invidx.bin parser -----

    private val invHeader = run {
        // Don't actually read here; just expose via lazy properties.
    }

    private val invPostingsOffset: Int by lazy {
        require(invBuf.getInt(0) == 0x494E5631) { "invidx.bin bad magic" }
        invBuf.getInt(12)
    }

    private fun invPostingsRange(termIdx: Int): IntArray {
        val base = 16 + termIdx * 4
        val start = invBuf.getInt(base)
        val end = invBuf.getInt(base + 4)
        return intArrayOf(invPostingsOffset + start, invPostingsOffset + end)
    }

    // ----- KNN -----

    data class Hit(val rowIdx: Int, val similarity: Float)

    // ----- IVF -----

    private val ivfNlist: Int? by lazy {
        listsBuf?.let { b ->
            require(b.getInt(0) == 0x49564631) { "ivf.lists bad magic" }
            b.getInt(8)
        }
    }

    /** Read the start/end row-index byte offsets for inverted list `c`. */
    private fun ivfListRowsRange(c: Int): Pair<Int, Int>? {
        val b = listsBuf ?: return null
        val offsetsOff = b.getInt(12)
        val startIdx = b.getInt(offsetsOff + c * 4)
        val endIdx = b.getInt(offsetsOff + (c + 1) * 4)
        val rowsBase = offsetsOff + ((ivfNlist ?: 0) + 1) * 4
        return Pair(rowsBase + startIdx * 4, rowsBase + endIdx * 4)
    }

    /** Reusable scratch — avoids allocating a 1000-float array per query. */
    private var scratchQ: FloatArray? = null
    private fun scratchQ(): FloatArray {
        val K = ldaDim
        val s = scratchQ
        if (s != null && s.size == K) return s
        val n = FloatArray(K); scratchQ = n; return n
    }

    /** Decode T[rowIdx] into `into` (must be size K). */
    private fun readTRowInto(rowIdx: Int, into: FloatArray) {
        val K = ldaDim
        val off = rowIdx * K * 2
        for (k in 0 until K) {
            val h = tBuf.getShort(off + k * 2).toInt() and 0xFFFF
            into[k] = halfToFloat(h)
        }
    }

    /** Inline work_idx for row `i` — skips the RowMeta data-class allocation. */
    private fun workIdxOf(rowIdx: Int): Int = rmBuf.getInt(16 + rowIdx * 20 + 4)

    /** LDA KNN via IVF only. If the pack lacks centroids/lists this returns
     *  empty — no brute-force fallback. Excludes same-work and tiny-bag rows. */
    fun ldaKnn(srcRowIdx: Int, K: Int, minSim: Float, nprobe: Int = 10): List<Hit> {
        if (srcRowIdx < 0 || srcRowIdx >= passageCount) return emptyList()
        val centroids = centroidsBuf ?: return emptyList()
        val nlist = ivfNlist ?: return emptyList()
        val lists = listsBuf ?: return emptyList()

        val q = scratchQ()
        readTRowInto(srcRowIdx, q)
        val srcWork = workIdxOf(srcRowIdx)
        val Kdim = ldaDim

        // 1) score q against every centroid
        val centroidSims = FloatArray(nlist)
        for (c in 0 until nlist) {
            val off = c * Kdim * 2
            var sum = 0f
            for (k in 0 until Kdim) {
                val h = centroids.getShort(off + k * 2).toInt() and 0xFFFF
                sum += halfToFloat(h) * q[k]
            }
            centroidSims[c] = sum
        }
        // 2) pick top nprobe centroids
        val nprobeEff = minOf(nprobe, nlist)
        val cTop = TopKHeap(nprobeEff)
        for (c in 0 until nlist) cTop.offer(c, centroidSims[c])
        val pickedCentroids = cTop.toList().map { it.rowIdx }
        // 3) score only the rows in those centroids' lists
        val heap = TopKHeap(K)
        for (c in pickedCentroids) {
            val range = ivfListRowsRange(c) ?: continue
            var off = range.first
            while (off < range.second) {
                val i = lists.getInt(off); off += 4
                if (i == srcRowIdx) continue
                if (workIdxOf(i) == srcWork) continue
                val rowOff = i * Kdim * 2
                var sum = 0f
                for (k in 0 until Kdim) {
                    val h = tBuf.getShort(rowOff + k * 2).toInt() and 0xFFFF
                    sum += halfToFloat(h) * q[k]
                }
                if (sum > minSim) heap.offer(i, sum)
            }
        }
        return heap.toList()
    }

    /** Pre-built (term_idx -> tf) bag for source row, read from bags.bin.
     *  Returns empty map if bags.bin isn't shipped or row is out of range. */
    fun sourceBag(rowIdx: Int): Map<Int, Int> {
        val buf = bagsBuf ?: return emptyMap()
        if (rowIdx < 0 || rowIdx >= passageCount) return emptyMap()
        require(buf.getInt(0) == 0x42414731) { "bags.bin bad magic" }
        val recordCount = buf.getInt(8)
        if (rowIdx >= recordCount) return emptyMap()
        val entriesOffset = buf.getInt(12)
        val rowOffsetsBase = 16  // header is 16 bytes
        val startIdx = buf.getInt(rowOffsetsBase + rowIdx * 4)
        val endIdx = buf.getInt(rowOffsetsBase + (rowIdx + 1) * 4)
        val out = HashMap<Int, Int>((endIdx - startIdx) * 2)
        var off = entriesOffset + startIdx * 6
        for (i in startIdx until endIdx) {
            val termIdx = buf.getInt(off)
            val tf = buf.getShort(off + 4).toInt() and 0xFFFF
            out[termIdx] = tf
            off += 6
        }
        return out
    }

    /** TF-IDF KNN. `queryTf` is a term_idx -> tf map (usually from `sourceBag`).
     *  Walks the inverted index for each query term, accumulates row scores,
     *  filters by min_sim + same-work exclusion, returns top-K. */
    fun tfidfKnn(srcRowIdx: Int, queryTf: Map<Int, Int>, K: Int, minSim: Float): List<Hit> {
        if (srcRowIdx < 0 || srcRowIdx >= passageCount) return emptyList()
        if (queryTf.isEmpty()) return emptyList()
        val srcMeta = rowMeta(srcRowIdx)
        val tf = queryTf
        // sublinear_tf q-weights, then idf, then L2 normalize.
        val qWeights = HashMap<Int, Float>(tf.size * 2)
        var norm = 0.0
        for ((idx, c) in tf) {
            val w = (1.0 + Math.log(c.toDouble())) * vocabEntry(idx).idf
            qWeights[idx] = w.toFloat()
            norm += w * w
        }
        val nrm = Math.sqrt(norm).toFloat()
        if (nrm == 0f) return emptyList()
        for (idx in qWeights.keys.toList()) qWeights[idx] = qWeights[idx]!! / nrm

        // Walk each term's postings and accumulate into row-score.
        val sims = HashMap<Int, Float>()
        for ((termIdx, qw) in qWeights) {
            val range = invPostingsRange(termIdx)
            var off = range[0]
            val end = range[1]
            while (off < end) {
                val rowIdx = invBuf.getInt(off)
                val docW = halfToFloat(invBuf.getShort(off + 4).toInt() and 0xFFFF)
                off += 6
                if (rowIdx == srcRowIdx) continue
                sims.merge(rowIdx, qw * docW) { a, b -> a + b }
            }
        }
        if (sims.isEmpty()) return emptyList()

        val heap = TopKHeap(K)
        for ((rowIdx, s) in sims) {
            if (s <= minSim) continue
            val meta = rowMeta(rowIdx)
            if (meta.workIdx == srcMeta.workIdx) continue
            heap.offer(rowIdx, s)
        }
        return heap.toList()
    }

    // ----- entity kind: PROPN-only inverted index, parallel to TF-IDF -----

    private val entityVocabSize: Int by lazy {
        val v = entityVocBuf ?: return@lazy 0
        require(v.getInt(0) == 0x564F4331) { "entity_vocab.bin bad magic" }
        v.getInt(8)
    }

    private val entityVocabOffsets: IntArray by lazy {
        val v = entityVocBuf ?: return@lazy IntArray(0)
        val n = entityVocabSize
        val fileSize = v.capacity()
        val offArrayStart = fileSize - (n + 1) * 4
        val arr = IntArray(n + 1)
        for (i in 0..n) arr[i] = v.getInt(offArrayStart + i * 4)
        arr
    }

    private fun entityVocabEntry(idx: Int): VocabEntry {
        val v = entityVocBuf ?: error("entity_vocab.bin not loaded")
        val off = entityVocabOffsets[idx]
        val len = v.getShort(off).toInt() and 0xFFFF
        val b = ByteArray(len)
        val dup = v.duplicate(); dup.position(off + 2); dup.get(b)
        val term = String(b, Charsets.UTF_8)
        val idfH = v.getShort(off + 2 + len).toInt() and 0xFFFF
        return VocabEntry(term, halfToFloat(idfH))
    }

    private val entityInvPostingsOffset: Int by lazy {
        val iv = entityInvBuf ?: return@lazy 0
        require(iv.getInt(0) == 0x494E5631) { "entity_invidx.bin bad magic" }
        iv.getInt(12)
    }

    private fun entityInvPostingsRange(termIdx: Int): IntArray? {
        val iv = entityInvBuf ?: return null
        val base = 16 + termIdx * 4
        val start = iv.getInt(base)
        val end = iv.getInt(base + 4)
        return intArrayOf(entityInvPostingsOffset + start, entityInvPostingsOffset + end)
    }

    /** Pre-built (term_idx -> tf) PROPN bag for source row from
     *  `entity_bags.bin`. Empty if the file isn't shipped or the row has no
     *  proper nouns. */
    fun entitySourceBag(rowIdx: Int): Map<Int, Int> {
        val buf = entityBagsBuf ?: return emptyMap()
        if (rowIdx < 0 || rowIdx >= passageCount) return emptyMap()
        require(buf.getInt(0) == 0x42414731) { "entity_bags.bin bad magic" }
        val recordCount = buf.getInt(8)
        if (rowIdx >= recordCount) return emptyMap()
        val entriesOffset = buf.getInt(12)
        val rowOffsetsBase = 16
        val startIdx = buf.getInt(rowOffsetsBase + rowIdx * 4)
        val endIdx = buf.getInt(rowOffsetsBase + (rowIdx + 1) * 4)
        val out = HashMap<Int, Int>((endIdx - startIdx) * 2)
        var off = entriesOffset + startIdx * 6
        for (i in startIdx until endIdx) {
            val termIdx = buf.getInt(off)
            val tf = buf.getShort(off + 4).toInt() and 0xFFFF
            out[termIdx] = tf
            off += 6
        }
        return out
    }

    /** Entity-kind KNN. Identical algorithm to `tfidfKnn` but reads from
     *  entity_invidx.bin / entity_vocab.bin. Returns empty if any of the
     *  entity files are missing or the source bag is empty. */
    fun entityKnn(srcRowIdx: Int, queryTf: Map<Int, Int>, K: Int, minSim: Float): List<Hit> {
        if (srcRowIdx < 0 || srcRowIdx >= passageCount) return emptyList()
        if (queryTf.isEmpty()) return emptyList()
        val iv = entityInvBuf ?: return emptyList()
        val srcMeta = rowMeta(srcRowIdx)
        val qWeights = HashMap<Int, Float>(queryTf.size * 2)
        var norm = 0.0
        for ((idx, c) in queryTf) {
            val w = (1.0 + Math.log(c.toDouble())) * entityVocabEntry(idx).idf
            qWeights[idx] = w.toFloat()
            norm += w * w
        }
        val nrm = Math.sqrt(norm).toFloat()
        if (nrm == 0f) return emptyList()
        for (idx in qWeights.keys.toList()) qWeights[idx] = qWeights[idx]!! / nrm

        val sims = HashMap<Int, Float>()
        for ((termIdx, qw) in qWeights) {
            val range = entityInvPostingsRange(termIdx) ?: continue
            var off = range[0]
            val end = range[1]
            while (off < end) {
                val rowIdx = iv.getInt(off)
                val docW = halfToFloat(iv.getShort(off + 4).toInt() and 0xFFFF)
                off += 6
                if (rowIdx == srcRowIdx) continue
                sims.merge(rowIdx, qw * docW) { a, b -> a + b }
            }
        }
        if (sims.isEmpty()) return emptyList()

        val heap = TopKHeap(K)
        for ((rowIdx, s) in sims) {
            if (s <= minSim) continue
            val meta = rowMeta(rowIdx)
            if (meta.workIdx == srcMeta.workIdx) continue
            heap.offer(rowIdx, s)
        }
        return heap.toList()
    }

    // ----- end entity -----

    /** Top-K min-heap; offer keeps the K highest sims seen, returns sorted desc. */
    private class TopKHeap(val K: Int) {
        private val rows = IntArray(K)
        private val sims = FloatArray(K)
        private var n = 0
        fun offer(rowIdx: Int, sim: Float) {
            if (n < K) {
                rows[n] = rowIdx; sims[n] = sim
                n++
                if (n == K) heapify()
                return
            }
            if (sim <= sims[0]) return
            rows[0] = rowIdx; sims[0] = sim
            siftDown(0)
        }
        private fun heapify() { for (i in (K / 2 - 1) downTo 0) siftDown(i) }
        private fun siftDown(start: Int) {
            var i = start
            while (true) {
                val l = 2 * i + 1; val r = l + 1
                var m = i
                if (l < n && sims[l] < sims[m]) m = l
                if (r < n && sims[r] < sims[m]) m = r
                if (m == i) return
                val tr = rows[i]; rows[i] = rows[m]; rows[m] = tr
                val ts = sims[i]; sims[i] = sims[m]; sims[m] = ts
                i = m
            }
        }
        fun toList(): List<Hit> {
            val out = ArrayList<Hit>(n)
            for (i in 0 until n) out += Hit(rows[i], sims[i])
            out.sortByDescending { it.similarity }
            return out
        }
    }

    // ----- Public hit hydration -----

    data class HydratedHit(
        val bookId: String, val anchorLine: Int, val anchorSeq: Int,
        val authorId: String, val workId: String,
        val similarity: Float, val kind: String,
    )

    fun hydrate(hit: Hit, kind: String): HydratedHit {
        val m = rowMeta(hit.rowIdx)
        return HydratedHit(
            bookId = bookIds[m.anchorBookIdIdx],
            anchorLine = m.anchorLine,
            anchorSeq = m.anchorSeq,
            authorId = authorIds[m.authorIdx],
            workId = workIds[m.workIdx],
            similarity = hit.similarity,
            kind = kind,
        )
    }

    // ----- Manifest accessors -----

    val kindsAvailable: List<String> by lazy {
        val arr = manifest.optJSONArray("kinds_available")
        if (arr == null) emptyList()
        else (0 until arr.length()).map { arr.getString(it) }
    }

    val defaultKind: String by lazy {
        manifest.optString("default_kind", "lda")
    }

    fun kindUiLabel(kind: String): String =
        manifest.optJSONObject("kind_labels")?.optJSONObject(kind)?.optString("ui") ?: kind

    fun kindUiHint(kind: String): String =
        manifest.optJSONObject("kind_labels")?.optJSONObject(kind)?.optString("hint") ?: ""

    val ldaMinSim: Float by lazy { manifest.optDouble("lda_min_sim", 0.5).toFloat() }
    val tfidfMinSim: Float by lazy { manifest.optDouble("tfidf_min_sim", 0.15).toFloat() }
    val entityMinSim: Float by lazy { manifest.optDouble("entity_min_sim", 0.20).toFloat() }
}
