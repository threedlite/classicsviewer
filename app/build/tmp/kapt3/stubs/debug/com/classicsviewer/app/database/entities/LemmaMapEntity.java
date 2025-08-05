package com.classicsviewer.app.database.entities;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010\u0006\n\u0002\b\u0015\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0002\b\u0087\b\u0018\u00002\u00020\u0001BA\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0003\u0012\u0006\u0010\u0005\u001a\u00020\u0003\u0012\n\b\u0002\u0010\u0006\u001a\u0004\u0018\u00010\u0007\u0012\n\b\u0002\u0010\b\u001a\u0004\u0018\u00010\u0003\u0012\n\b\u0002\u0010\t\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\u0002\u0010\nJ\t\u0010\u0014\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0015\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0016\u001a\u00020\u0003H\u00c6\u0003J\u0010\u0010\u0017\u001a\u0004\u0018\u00010\u0007H\u00c6\u0003\u00a2\u0006\u0002\u0010\fJ\u000b\u0010\u0018\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003J\u000b\u0010\u0019\u001a\u0004\u0018\u00010\u0003H\u00c6\u0003JP\u0010\u001a\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00032\n\b\u0002\u0010\u0006\u001a\u0004\u0018\u00010\u00072\n\b\u0002\u0010\b\u001a\u0004\u0018\u00010\u00032\n\b\u0002\u0010\t\u001a\u0004\u0018\u00010\u0003H\u00c6\u0001\u00a2\u0006\u0002\u0010\u001bJ\u0013\u0010\u001c\u001a\u00020\u001d2\b\u0010\u001e\u001a\u0004\u0018\u00010\u0001H\u00d6\u0003J\t\u0010\u001f\u001a\u00020 H\u00d6\u0001J\t\u0010!\u001a\u00020\u0003H\u00d6\u0001R\u0015\u0010\u0006\u001a\u0004\u0018\u00010\u0007\u00a2\u0006\n\n\u0002\u0010\r\u001a\u0004\b\u000b\u0010\fR\u0011\u0010\u0005\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\u000fR\u0018\u0010\t\u001a\u0004\u0018\u00010\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\u000fR\u0013\u0010\b\u001a\u0004\u0018\u00010\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u000fR\u0016\u0010\u0002\u001a\u00020\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\u000fR\u0016\u0010\u0004\u001a\u00020\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u000f\u00a8\u0006\""}, d2 = {"Lcom/classicsviewer/app/database/entities/LemmaMapEntity;", "", "wordForm", "", "wordNormalized", "lemma", "confidence", "", "source", "morphInfo", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/Double;Ljava/lang/String;Ljava/lang/String;)V", "getConfidence", "()Ljava/lang/Double;", "Ljava/lang/Double;", "getLemma", "()Ljava/lang/String;", "getMorphInfo", "getSource", "getWordForm", "getWordNormalized", "component1", "component2", "component3", "component4", "component5", "component6", "copy", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/Double;Ljava/lang/String;Ljava/lang/String;)Lcom/classicsviewer/app/database/entities/LemmaMapEntity;", "equals", "", "other", "hashCode", "", "toString", "app_debug"})
@androidx.room.Entity(tableName = "lemma_map", primaryKeys = {"word_form", "lemma"}, indices = {@androidx.room.Index(value = {"word_form"}, name = "idx_lemma_map_word"), @androidx.room.Index(value = {"lemma"}, name = "idx_lemma_map_lemma")})
public final class LemmaMapEntity {
    @androidx.room.ColumnInfo(name = "word_form")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String wordForm = null;
    @androidx.room.ColumnInfo(name = "word_normalized")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String wordNormalized = null;
    @org.jetbrains.annotations.NotNull
    private final java.lang.String lemma = null;
    @org.jetbrains.annotations.Nullable
    private final java.lang.Double confidence = null;
    @org.jetbrains.annotations.Nullable
    private final java.lang.String source = null;
    @androidx.room.ColumnInfo(name = "morph_info")
    @org.jetbrains.annotations.Nullable
    private final java.lang.String morphInfo = null;
    
    public LemmaMapEntity(@org.jetbrains.annotations.NotNull
    java.lang.String wordForm, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    java.lang.String lemma, @org.jetbrains.annotations.Nullable
    java.lang.Double confidence, @org.jetbrains.annotations.Nullable
    java.lang.String source, @org.jetbrains.annotations.Nullable
    java.lang.String morphInfo) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getWordForm() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getWordNormalized() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getLemma() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.Double getConfidence() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String getSource() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String getMorphInfo() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String component1() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String component2() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String component3() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.Double component4() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String component5() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String component6() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final com.classicsviewer.app.database.entities.LemmaMapEntity copy(@org.jetbrains.annotations.NotNull
    java.lang.String wordForm, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    java.lang.String lemma, @org.jetbrains.annotations.Nullable
    java.lang.Double confidence, @org.jetbrains.annotations.Nullable
    java.lang.String source, @org.jetbrains.annotations.Nullable
    java.lang.String morphInfo) {
        return null;
    }
    
    @java.lang.Override
    public boolean equals(@org.jetbrains.annotations.Nullable
    java.lang.Object other) {
        return false;
    }
    
    @java.lang.Override
    public int hashCode() {
        return 0;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.NotNull
    public java.lang.String toString() {
        return null;
    }
}