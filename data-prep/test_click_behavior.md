# Dictionary Click Behavior Issue Analysis

## Symptoms
- Sometimes clicking on words doesn't trigger the dictionary lookup
- No error messages in logs
- Dictionary activity launches successfully when it does work

## Potential Causes

1. **Touch Event Conflicts**
   - The RecyclerView might be intercepting touch events
   - Scroll events might be consuming the click

2. **LinkMovementMethod Issues**
   - Known Android issue where LinkMovementMethod sometimes doesn't register clicks properly
   - Can happen when the TextView is in a scrollable container

3. **Span Boundaries**
   - Word boundaries might not be calculated correctly for some texts
   - Overlapping spans could cause issues

## Debugging Steps

1. Add logging to the click handler:
```kotlin
private inner class NoUnderlineClickableSpan(
    private val onClick: () -> Unit
) : ClickableSpan() {
    override fun onClick(widget: View) {
        Log.d("TextLineAdapter", "Click registered on word")
        onClick()
    }
}
```

2. Check if touch events are being received:
```kotlin
holder.binding.lineText.setOnTouchListener { v, event ->
    Log.d("TextLineAdapter", "Touch event: ${event.action}")
    false // Let LinkMovementMethod handle it
}
```

3. Consider alternative approaches:
   - Custom touch handling instead of LinkMovementMethod
   - Make entire TextView clickable with word detection on click
   - Use a different span type or custom movement method

## Recommended Fix

The most reliable approach would be to implement a custom touch handler that:
1. Detects the word at the touch position
2. Handles both tap and long-press
3. Provides visual feedback
4. Works reliably in scrollable containers