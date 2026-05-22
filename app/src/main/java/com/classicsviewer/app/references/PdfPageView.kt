package com.classicsviewer.app.references

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.util.AttributeSet
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import java.io.File

/**
 * Custom view that renders a single PDF page using PdfRenderer.
 *
 * Architecture (per design doc §6):
 *  - One Bitmap at a time, rendered at 3x fit-width in RGB_565.
 *  - Pinch-zoom 1.0x..3.0x, applied via a Matrix on a fixed bitmap (no re-render).
 *  - Double-tap toggles between 1.0x and 2.5x.
 *  - At zoom == 1.0, horizontal flings turn pages; otherwise scrolling pans.
 *  - Bitmap pan is clamped so the page never leaves the visible area.
 */
class PdfPageView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    interface Listener {
        fun onPageChanged(pageIndex: Int)
    }

    companion object {
        const val MIN_ZOOM = 1.0f
        const val MAX_ZOOM = 3.0f
        const val DOUBLE_TAP_ZOOM = 2.5f
        // PdfRenderer only supports ARGB_8888 / ALPHA_8 (RGB_565 throws
        // "Unsupported pixel format"). Render scale matches max zoom so every
        // pixel on screen comes from a real rendered pixel when bitmap fits
        // under the hard cap below — no upscale blur in the 1×–3× range.
        private const val RENDER_SCALE = 3
        // Hard cap on bitmap dimensions to guarantee bounded memory regardless
        // of screen size. 4096×4096 ARGB_8888 = 64 MB worst case. Above this,
        // baseScale adjusts so the bitmap still fits-width at zoom 1.0; at the
        // very high zoom end on a huge screen, the bitmap is mildly upscaled
        // (matrix-only) instead of blowing the memory budget.
        private const val MAX_BITMAP_DIMENSION = 4096
    }

    var listener: Listener? = null

    private var renderer: PdfRenderer? = null
    private var pfd: ParcelFileDescriptor? = null
    private var currentPage: PdfRenderer.Page? = null
    private var currentPageIndex: Int = 0
    private var bitmap: Bitmap? = null

    private val matrix = Matrix()
    private val drawPaint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG)

    private var zoom: Float = 1.0f
    private var scrollX: Float = 0f // page-coordinate units at zoom 1.0
    private var scrollY: Float = 0f

    // Pending state restored before bitmap is ready
    private var pendingZoom: Float? = null
    private var pendingScrollX: Float? = null
    private var pendingScrollY: Float? = null

    private val scaleGestureDetector = ScaleGestureDetector(
        context,
        object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScale(detector: ScaleGestureDetector): Boolean {
                applyZoom(zoom * detector.scaleFactor, detector.focusX, detector.focusY)
                return true
            }
        }
    )

    private val gestureDetector = GestureDetector(
        context,
        object : GestureDetector.SimpleOnGestureListener() {
            override fun onDown(e: MotionEvent): Boolean = true

            override fun onScroll(
                e1: MotionEvent?,
                e2: MotionEvent,
                distanceX: Float,
                distanceY: Float,
            ): Boolean {
                // Always allow drag-to-pan; clampMatrix below enforces page bounds
                // so a drag never moves the bitmap off-screen. Page navigation is
                // handled by the toolbar prev/next buttons and the right-edge
                // slider — gestures are pan-only.
                matrix.postTranslate(-distanceX, -distanceY)
                clampMatrix()
                syncScrollFromMatrix()
                invalidate()
                return true
            }

            override fun onDoubleTap(e: MotionEvent): Boolean {
                val target = if (zoom > MIN_ZOOM + 0.01f) MIN_ZOOM else DOUBLE_TAP_ZOOM
                applyZoom(target, e.x, e.y)
                return true
            }
        }
    )

    init {
        setBackgroundColor(Color.BLACK)
    }

    fun open(file: File, pageIndex: Int, zoom: Float, scrollX: Float, scrollY: Float) {
        close()
        pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
        renderer = PdfRenderer(pfd!!)
        currentPageIndex = pageIndex.coerceIn(0, (renderer!!.pageCount - 1).coerceAtLeast(0))
        pendingZoom = zoom
        pendingScrollX = scrollX
        pendingScrollY = scrollY
        // Bitmap is created in onSizeChanged once we know the view size.
        if (width > 0 && height > 0) renderCurrentPage()
        invalidate()
    }

    fun close() {
        currentPage?.close()
        currentPage = null
        renderer?.close()
        renderer = null
        pfd?.close()
        pfd = null
        bitmap?.recycle()
        bitmap = null
    }

    fun pageIndex(): Int = currentPageIndex

    fun pageCount(): Int = renderer?.pageCount ?: 0

    fun currentZoom(): Float = zoom

    fun currentScrollX(): Float = scrollX

    fun currentScrollY(): Float = scrollY

    fun goToPage(index: Int) {
        val r = renderer ?: return
        val target = index.coerceIn(0, r.pageCount - 1)
        if (target == currentPageIndex && bitmap != null) return
        currentPageIndex = target
        zoom = MIN_ZOOM
        scrollX = 0f
        scrollY = 0f
        pendingZoom = null
        pendingScrollX = null
        pendingScrollY = null
        renderCurrentPage()
        invalidate()
        listener?.onPageChanged(currentPageIndex)
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        if (renderer != null && w > 0 && h > 0) {
            renderCurrentPage()
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        bitmap?.let { canvas.drawBitmap(it, matrix, drawPaint) }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        scaleGestureDetector.onTouchEvent(event)
        gestureDetector.onTouchEvent(event)
        return true
    }

    private fun renderCurrentPage() {
        val r = renderer ?: return
        if (width == 0 || height == 0) return
        currentPage?.close()
        val page = r.openPage(currentPageIndex)
        currentPage = page

        val pageW = page.width.toFloat().coerceAtLeast(1f)
        val pageH = page.height.toFloat().coerceAtLeast(1f)
        val pageAspect = pageH / pageW

        // Render at view_width × RENDER_SCALE, but cap each dimension at
        // MAX_BITMAP_DIMENSION so a 10" tablet doesn't try to allocate
        // ~300 MB per page. Width is the binding constraint at 3:4 portrait
        // aspect; height check covers narrow-tall pages.
        val desiredW = (width * RENDER_SCALE).coerceAtLeast(1)
        val desiredH = (desiredW * pageAspect).coerceAtLeast(1f).toInt()
        val capRatioW = MAX_BITMAP_DIMENSION.toFloat() / desiredW
        val capRatioH = MAX_BITMAP_DIMENSION.toFloat() / desiredH
        val capRatio = minOf(1f, capRatioW, capRatioH)
        var bmpWidth = (desiredW * capRatio).toInt().coerceAtLeast(1)
        var bmpHeight = (bmpWidth * pageAspect).toInt().coerceAtLeast(1)

        bitmap?.recycle()
        bitmap = null
        // PdfRenderer requires ARGB_8888 (or ALPHA_8); RGB_565 throws
        // IllegalArgumentException: Unsupported pixel format. If even the
        // capped allocation fails (native heap pressure), halve until it
        // fits — better degraded sharpness than a crash.
        var bmp: Bitmap? = null
        var attemptW = bmpWidth
        var attemptH = bmpHeight
        while (bmp == null && attemptW > 256 && attemptH > 256) {
            bmp = try {
                Bitmap.createBitmap(attemptW, attemptH, Bitmap.Config.ARGB_8888)
            } catch (oom: OutOfMemoryError) {
                attemptW /= 2
                attemptH /= 2
                null
            }
        }
        if (bmp == null) return
        bmpWidth = bmp.width
        bmpHeight = bmp.height
        bmp.eraseColor(Color.WHITE)
        page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
        bitmap = bmp

        // Dynamic baseScale: bitmap fills view width exactly at zoom 1.0,
        // regardless of how aggressively we capped the bitmap size. This
        // means on huge screens the bitmap may be upscaled past 2x or so
        // at zoom 3 (mild blur), but it never wastes memory.
        matrix.reset()
        val baseScale = width.toFloat() / bmpWidth.toFloat()
        matrix.postScale(baseScale, baseScale)

        val targetZoom = pendingZoom ?: MIN_ZOOM
        val targetSX = pendingScrollX ?: 0f
        val targetSY = pendingScrollY ?: 0f
        pendingZoom = null
        pendingScrollX = null
        pendingScrollY = null

        if (targetZoom > MIN_ZOOM + 0.001f) {
            matrix.postScale(targetZoom, targetZoom, 0f, 0f)
        }
        zoom = targetZoom.coerceIn(MIN_ZOOM, MAX_ZOOM)

        // Translate using page-space scroll values: scrollX/Y are in display-coordinate units at zoom 1.0.
        // After current zoom is applied, translate by -scroll * zoom to bring that offset on screen.
        matrix.postTranslate(-targetSX * zoom, -targetSY * zoom)
        clampMatrix()
        syncScrollFromMatrix()
    }

    private fun applyZoom(targetZoom: Float, focusX: Float, focusY: Float) {
        val clamped = targetZoom.coerceIn(MIN_ZOOM, MAX_ZOOM)
        if (clamped == zoom) return
        val factor = clamped / zoom
        matrix.postScale(factor, factor, focusX, focusY)
        zoom = clamped
        clampMatrix()
        syncScrollFromMatrix()
        invalidate()
    }

    /**
     * Clamp matrix translation so the bitmap stays within the view bounds:
     *  - If the displayed bitmap is wider than the view, edges can sit anywhere
     *    between left=0 and right=viewWidth.
     *  - If narrower (shouldn't happen at zoom >= 1.0 with fit-width base),
     *    center horizontally.
     *  - Same logic vertically.
     */
    private fun clampMatrix() {
        val bmp = bitmap ?: return
        val values = FloatArray(9)
        matrix.getValues(values)
        val scaleX = values[Matrix.MSCALE_X]
        val scaleY = values[Matrix.MSCALE_Y]
        val transX = values[Matrix.MTRANS_X]
        val transY = values[Matrix.MTRANS_Y]

        val displayedW = bmp.width * scaleX
        val displayedH = bmp.height * scaleY

        var newTransX = transX
        var newTransY = transY

        if (displayedW <= width) {
            newTransX = (width - displayedW) / 2f
        } else {
            val minX = width - displayedW
            val maxX = 0f
            if (newTransX < minX) newTransX = minX
            if (newTransX > maxX) newTransX = maxX
        }

        if (displayedH <= height) {
            newTransY = (height - displayedH) / 2f
        } else {
            val minY = height - displayedH
            val maxY = 0f
            if (newTransY < minY) newTransY = minY
            if (newTransY > maxY) newTransY = maxY
        }

        if (newTransX != transX || newTransY != transY) {
            values[Matrix.MTRANS_X] = newTransX
            values[Matrix.MTRANS_Y] = newTransY
            matrix.setValues(values)
        }
    }

    /**
     * Derive scrollX/scrollY (in view-coordinate units at zoom 1.0) from the current matrix.
     * The matrix's translation is in pixels at the current zoom; divide by zoom to keep it stable
     * across rotation and zoom changes.
     */
    private fun syncScrollFromMatrix() {
        val bmp = bitmap ?: return
        val values = FloatArray(9)
        matrix.getValues(values)
        // Read the bitmap's effective scale directly from the matrix so this
        // works whether RENDER_SCALE or the MAX_BITMAP_DIMENSION cap is the
        // binding constraint. effectiveScale equals baseScale × zoom.
        val effectiveScale = values[Matrix.MSCALE_X]
        val transX = values[Matrix.MTRANS_X]
        val transY = values[Matrix.MTRANS_Y]
        // scrollX/Y are stored in view-pixel units at zoom 1.0 so they remain
        // stable across rotation, device, and bitmap-size differences.
        scrollX = -transX / zoom
        scrollY = -transY / zoom

        if (bmp.width * effectiveScale <= width) scrollX = 0f
        if (bmp.height * effectiveScale <= height) scrollY = 0f
    }
}
