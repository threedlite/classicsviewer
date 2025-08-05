package com.classicsviewer.app.data;

/**
 * Helper class for handling database stored in OBB expansion files
 */
@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000@\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u0007\n\u0002\u0010\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\t\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0004\u0018\u0000 \u00172\u00020\u0001:\u0001\u0017B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J)\u0010\u0005\u001a\u00020\u00062\u0016\b\u0002\u0010\u0007\u001a\u0010\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\n\u0018\u00010\bH\u0086@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u000bJ.\u0010\f\u001a\u00020\n2\u0006\u0010\r\u001a\u00020\u000e2\u0006\u0010\u000f\u001a\u00020\u000e2\u0014\u0010\u0007\u001a\u0010\u0012\u0004\u0012\u00020\t\u0012\u0004\u0012\u00020\n\u0018\u00010\bH\u0002J\u0006\u0010\u0010\u001a\u00020\u0011J\b\u0010\u0012\u001a\u0004\u0018\u00010\u000eJ\u0006\u0010\u0013\u001a\u00020\u0014J\u0006\u0010\u0015\u001a\u00020\u0006J\u0006\u0010\u0016\u001a\u00020\u0006R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\u0018"}, d2 = {"Lcom/classicsviewer/app/data/ObbDatabaseHelper;", "", "context", "Landroid/content/Context;", "(Landroid/content/Context;)V", "extractDatabaseFromObb", "", "progressCallback", "Lkotlin/Function1;", "", "", "(Lkotlin/jvm/functions/Function1;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "extractFromZip", "zipFile", "Ljava/io/File;", "targetDb", "getExpectedObbSize", "", "getObbDatabasePath", "getObbDirectoryPath", "", "isObbAvailable", "validateObbFile", "Companion", "app_debug"})
public final class ObbDatabaseHelper {
    @org.jetbrains.annotations.NotNull
    private final android.content.Context context = null;
    private static final int OBB_VERSION = 1;
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String DB_NAME = "perseus_texts.db";
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.data.ObbDatabaseHelper.Companion Companion = null;
    
    public ObbDatabaseHelper(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        super();
    }
    
    /**
     * Get the path to the OBB file if it exists
     */
    @org.jetbrains.annotations.Nullable
    public final java.io.File getObbDatabasePath() {
        return null;
    }
    
    /**
     * Check if OBB file exists
     */
    public final boolean isObbAvailable() {
        return false;
    }
    
    /**
     * Extract database from OBB file to internal storage
     * Now supports both compressed (ZIP) and uncompressed OBB files
     */
    @org.jetbrains.annotations.Nullable
    public final java.lang.Object extractDatabaseFromObb(@org.jetbrains.annotations.Nullable
    kotlin.jvm.functions.Function1<? super java.lang.Float, kotlin.Unit> progressCallback, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Boolean> $completion) {
        return null;
    }
    
    private final void extractFromZip(java.io.File zipFile, java.io.File targetDb, kotlin.jvm.functions.Function1<? super java.lang.Float, kotlin.Unit> progressCallback) {
    }
    
    /**
     * Get the expected OBB file size for validation
     */
    public final long getExpectedObbSize() {
        return 0L;
    }
    
    /**
     * Validate OBB file
     */
    public final boolean validateObbFile() {
        return false;
    }
    
    /**
     * Get OBB download directory path for user instructions
     */
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getObbDirectoryPath() {
        return null;
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0018\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\b\n\u0000\b\u0086\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082T\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0007"}, d2 = {"Lcom/classicsviewer/app/data/ObbDatabaseHelper$Companion;", "", "()V", "DB_NAME", "", "OBB_VERSION", "", "app_debug"})
    public static final class Companion {
        
        private Companion() {
            super();
        }
    }
}