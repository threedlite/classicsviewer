package com.classicsviewer.app.references

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View

/**
 * Vertical slider for rapidly navigating to any page in a PDF.
 *
 *  - User drags the thumb along a vertical track on the right edge.
 *  - `onDragProgress(page)` fires continuously while dragging so a centred
 *    preview label can show the target page number without re-rendering.
 *  - `onPageSelected(page)` fires once on release; the host then jumps to
 *    that page (rendering only once at the final position).
 *
 * Pages are 0-indexed in callbacks.
 */
class VerticalPageSlider @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0,
) : View(context, attrs, defStyleAttr) {

    var pageCount: Int = 1
        set(value) {
            field = value.coerceAtLeast(1)
            invalidate()
        }

    var currentPage: Int = 0
        set(value) {
            field = value.coerceIn(0, pageCount - 1)
            if (!isDragging) invalidate()
        }

    var onDragProgress: (Int) -> Unit = {}
    var onPageSelected: (Int) -> Unit = {}
    var onDragStateChanged: (Boolean) -> Unit = {}

    private val trackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x66FFFFFF.toInt()
        style = Paint.Style.FILL
    }
    private val thumbPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }
    private val thumbBorderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xCC000000.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }

    private var isDragging: Boolean = false
    private var dragPage: Int = 0

    private val trackRect = RectF()
    private val thumbRect = RectF()

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        val trackWidth = 6f
        val padding = 16f
        val trackLeft = (w - trackWidth) / 2f
        trackRect.set(trackLeft, padding, trackLeft + trackWidth, h - padding)
        canvas.drawRoundRect(trackRect, trackWidth / 2f, trackWidth / 2f, trackPaint)

        val displayedPage = if (isDragging) dragPage else currentPage
        val frac = if (pageCount > 1) {
            displayedPage.toFloat() / (pageCount - 1).toFloat()
        } else 0f
        val thumbCenterY = padding + frac * (h - 2 * padding)
        val thumbHalfHeight = if (isDragging) 24f else 16f
        val thumbHalfWidth = if (isDragging) 28f else 20f
        thumbRect.set(
            (w / 2f) - thumbHalfWidth,
            thumbCenterY - thumbHalfHeight,
            (w / 2f) + thumbHalfWidth,
            thumbCenterY + thumbHalfHeight,
        )
        canvas.drawRoundRect(thumbRect, 6f, 6f, thumbPaint)
        canvas.drawRoundRect(thumbRect, 6f, 6f, thumbBorderPaint)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                isDragging = true
                onDragStateChanged(true)
                updatePageFromY(event.y)
                parent?.requestDisallowInterceptTouchEvent(true)
                invalidate()
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                if (isDragging) {
                    updatePageFromY(event.y)
                    invalidate()
                }
                return true
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                if (isDragging) {
                    isDragging = false
                    onDragStateChanged(false)
                    val target = dragPage.coerceIn(0, pageCount - 1)
                    currentPage = target
                    onPageSelected(target)
                    parent?.requestDisallowInterceptTouchEvent(false)
                    invalidate()
                }
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    private fun updatePageFromY(y: Float) {
        val padding = 16f
        val usable = (height - 2 * padding).coerceAtLeast(1f)
        val frac = ((y - padding) / usable).coerceIn(0f, 1f)
        val target = (frac * (pageCount - 1)).toInt().coerceIn(0, pageCount - 1)
        if (target != dragPage) {
            dragPage = target
            onDragProgress(target)
        }
    }
}
