package com.classicsviewer.app.database.entities;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000&\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\t\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\b\n\u0002\b\u0018\n\u0002\u0010\u000b\n\u0002\b\u0004\b\u0087\b\u0018\u00002\u00020\u0001B;\u0012\b\b\u0002\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\u0006\u0010\u0006\u001a\u00020\u0007\u0012\b\u0010\b\u001a\u0004\u0018\u00010\u0007\u0012\u0006\u0010\t\u001a\u00020\u0005\u0012\b\u0010\n\u001a\u0004\u0018\u00010\u0005\u00a2\u0006\u0002\u0010\u000bJ\t\u0010\u0017\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0018\u001a\u00020\u0005H\u00c6\u0003J\t\u0010\u0019\u001a\u00020\u0007H\u00c6\u0003J\u0010\u0010\u001a\u001a\u0004\u0018\u00010\u0007H\u00c6\u0003\u00a2\u0006\u0002\u0010\u000fJ\t\u0010\u001b\u001a\u00020\u0005H\u00c6\u0003J\u000b\u0010\u001c\u001a\u0004\u0018\u00010\u0005H\u00c6\u0003JN\u0010\u001d\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00052\b\b\u0002\u0010\u0006\u001a\u00020\u00072\n\b\u0002\u0010\b\u001a\u0004\u0018\u00010\u00072\b\b\u0002\u0010\t\u001a\u00020\u00052\n\b\u0002\u0010\n\u001a\u0004\u0018\u00010\u0005H\u00c6\u0001\u00a2\u0006\u0002\u0010\u001eJ\u0013\u0010\u001f\u001a\u00020 2\b\u0010!\u001a\u0004\u0018\u00010\u0001H\u00d6\u0003J\t\u0010\"\u001a\u00020\u0007H\u00d6\u0001J\t\u0010#\u001a\u00020\u0005H\u00d6\u0001R\u0016\u0010\u0004\u001a\u00020\u00058\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\f\u0010\rR\u001a\u0010\b\u001a\u0004\u0018\u00010\u00078\u0006X\u0087\u0004\u00a2\u0006\n\n\u0002\u0010\u0010\u001a\u0004\b\u000e\u0010\u000fR\u0016\u0010\u0002\u001a\u00020\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u0012R\u0016\u0010\u0006\u001a\u00020\u00078\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\u0014R\u0016\u0010\t\u001a\u00020\u00058\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0015\u0010\rR\u0013\u0010\n\u001a\u0004\u0018\u00010\u0005\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0016\u0010\r\u00a8\u0006$"}, d2 = {"Lcom/classicsviewer/app/database/entities/TranslationSegmentEntity;", "", "id", "", "bookId", "", "startLine", "", "endLine", "translationText", "translator", "(JLjava/lang/String;ILjava/lang/Integer;Ljava/lang/String;Ljava/lang/String;)V", "getBookId", "()Ljava/lang/String;", "getEndLine", "()Ljava/lang/Integer;", "Ljava/lang/Integer;", "getId", "()J", "getStartLine", "()I", "getTranslationText", "getTranslator", "component1", "component2", "component3", "component4", "component5", "component6", "copy", "(JLjava/lang/String;ILjava/lang/Integer;Ljava/lang/String;Ljava/lang/String;)Lcom/classicsviewer/app/database/entities/TranslationSegmentEntity;", "equals", "", "other", "hashCode", "toString", "app_debug"})
@androidx.room.Entity(tableName = "translation_segments", foreignKeys = {@androidx.room.ForeignKey(entity = com.classicsviewer.app.database.entities.BookEntity.class, parentColumns = {"id"}, childColumns = {"book_id"}, onDelete = 5)}, indices = {@androidx.room.Index(value = {"book_id"}, name = "idx_translation_segments_book"), @androidx.room.Index(value = {"book_id", "start_line"}, name = "idx_translation_segments_lines")})
public final class TranslationSegmentEntity {
    @androidx.room.PrimaryKey(autoGenerate = true)
    private final long id = 0L;
    @androidx.room.ColumnInfo(name = "book_id")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String bookId = null;
    @androidx.room.ColumnInfo(name = "start_line")
    private final int startLine = 0;
    @androidx.room.ColumnInfo(name = "end_line")
    @org.jetbrains.annotations.Nullable
    private final java.lang.Integer endLine = null;
    @androidx.room.ColumnInfo(name = "translation_text")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String translationText = null;
    @org.jetbrains.annotations.Nullable
    private final java.lang.String translator = null;
    
    public TranslationSegmentEntity(long id, @org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, @org.jetbrains.annotations.Nullable
    java.lang.Integer endLine, @org.jetbrains.annotations.NotNull
    java.lang.String translationText, @org.jetbrains.annotations.Nullable
    java.lang.String translator) {
        super();
    }
    
    public final long getId() {
        return 0L;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getBookId() {
        return null;
    }
    
    public final int getStartLine() {
        return 0;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.Integer getEndLine() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getTranslationText() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String getTranslator() {
        return null;
    }
    
    public final long component1() {
        return 0L;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String component2() {
        return null;
    }
    
    public final int component3() {
        return 0;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.Integer component4() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String component5() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable
    public final java.lang.String component6() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final com.classicsviewer.app.database.entities.TranslationSegmentEntity copy(long id, @org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, @org.jetbrains.annotations.Nullable
    java.lang.Integer endLine, @org.jetbrains.annotations.NotNull
    java.lang.String translationText, @org.jetbrains.annotations.Nullable
    java.lang.String translator) {
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