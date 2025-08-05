package com.classicsviewer.app.utils;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00006\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0002\b\u0003\b\u00c6\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J0\u0010\u0007\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\f2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\f2\b\b\u0002\u0010\u0010\u001a\u00020\u0011J0\u0010\u0012\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\n2\u0006\u0010\u0013\u001a\u00020\f2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\f2\b\b\u0002\u0010\u0010\u001a\u00020\u0011R\u0016\u0010\u0003\u001a\n \u0005*\u0004\u0018\u00010\u00040\u0004X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0016\u0010\u0006\u001a\n \u0005*\u0004\u0018\u00010\u00040\u0004X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0014"}, d2 = {"Lcom/classicsviewer/app/utils/DictionaryTextFormatter;", "", "()V", "ENGLISH_PATTERN", "Ljava/util/regex/Pattern;", "kotlin.jvm.PlatformType", "GREEK_PATTERN", "formatDictionaryText", "", "context", "Landroid/content/Context;", "text", "", "textView", "Landroid/widget/TextView;", "currentLanguage", "invertColors", "", "formatHtmlDictionaryText", "htmlText", "app_debug"})
public final class DictionaryTextFormatter {
    private static final java.util.regex.Pattern GREEK_PATTERN = null;
    private static final java.util.regex.Pattern ENGLISH_PATTERN = null;
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.utils.DictionaryTextFormatter INSTANCE = null;
    
    private DictionaryTextFormatter() {
        super();
    }
    
    public final void formatDictionaryText(@org.jetbrains.annotations.NotNull
    android.content.Context context, @org.jetbrains.annotations.NotNull
    java.lang.String text, @org.jetbrains.annotations.NotNull
    android.widget.TextView textView, @org.jetbrains.annotations.NotNull
    java.lang.String currentLanguage, boolean invertColors) {
    }
    
    public final void formatHtmlDictionaryText(@org.jetbrains.annotations.NotNull
    android.content.Context context, @org.jetbrains.annotations.NotNull
    java.lang.String htmlText, @org.jetbrains.annotations.NotNull
    android.widget.TextView textView, @org.jetbrains.annotations.NotNull
    java.lang.String currentLanguage, boolean invertColors) {
    }
}