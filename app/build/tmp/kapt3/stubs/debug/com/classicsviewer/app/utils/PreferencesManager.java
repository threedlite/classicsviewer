package com.classicsviewer.app.utils;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000<\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0005\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0007\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010$\n\u0000\n\u0002\u0018\u0002\n\u0002\b\b\b\u00c6\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J\u000e\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\fJ\u000e\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000b\u001a\u00020\fJ\u000e\u0010\u000f\u001a\u00020\u00102\u0006\u0010\u000b\u001a\u00020\fJ\u0010\u0010\u0011\u001a\u0004\u0018\u00010\u00042\u0006\u0010\u000b\u001a\u00020\fJ\u001a\u0010\u0012\u001a\u000e\u0012\u0004\u0012\u00020\u0004\u0012\u0004\u0012\u00020\u00040\u00132\u0006\u0010\u000b\u001a\u00020\fJ\u0010\u0010\u0014\u001a\u00020\u00152\u0006\u0010\u000b\u001a\u00020\fH\u0002J*\u0010\u0016\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\f2\u0006\u0010\u0017\u001a\u00020\u00042\u0012\u0010\u0018\u001a\u000e\u0012\u0004\u0012\u00020\u0004\u0012\u0004\u0012\u00020\u00040\u0013J\u0016\u0010\u0019\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\f2\u0006\u0010\u001a\u001a\u00020\u000eJ\u0016\u0010\u001b\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\f2\u0006\u0010\u001c\u001a\u00020\u0010R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0007\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u001d"}, d2 = {"Lcom/classicsviewer/app/utils/PreferencesManager;", "", "()V", "KEY_FONT_SIZE", "", "KEY_INVERT_COLORS", "KEY_LAST_ACTIVITY", "KEY_LAST_EXTRAS", "PREFS_NAME", "clearNavigationState", "", "context", "Landroid/content/Context;", "getFontSize", "", "getInvertColors", "", "getLastActivity", "getLastExtras", "", "getPrefs", "Landroid/content/SharedPreferences;", "saveNavigationState", "activityName", "extras", "setFontSize", "size", "setInvertColors", "invert", "app_debug"})
public final class PreferencesManager {
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String PREFS_NAME = "ClassicsViewerPrefs";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String KEY_FONT_SIZE = "font_size";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String KEY_LAST_ACTIVITY = "last_activity";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String KEY_LAST_EXTRAS = "last_extras_";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String KEY_INVERT_COLORS = "invert_colors";
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.utils.PreferencesManager INSTANCE = null;
    
    private PreferencesManager() {
        super();
    }
    
    private final android.content.SharedPreferences getPrefs(android.content.Context context) {
        return null;
    }
    
    public final float getFontSize(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        return 0.0F;
    }
    
    public final void setFontSize(@org.jetbrains.annotations.NotNull
    android.content.Context context, float size) {
    }
    
    public final boolean getInvertColors(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        return false;
    }
    
    public final void setInvertColors(@org.jetbrains.annotations.NotNull
    android.content.Context context, boolean invert) {
    }
    
    public final void saveNavigationState(@org.jetbrains.annotations.NotNull
    android.content.Context context, @org.jetbrains.annotations.NotNull
    java.lang.String activityName, @org.jetbrains.annotations.NotNull
    java.util.Map<java.lang.String, java.lang.String> extras) {
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String getLastActivity(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.Map<java.lang.String, java.lang.String> getLastExtras(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        return null;
    }
    
    public final void clearNavigationState(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
    }
}