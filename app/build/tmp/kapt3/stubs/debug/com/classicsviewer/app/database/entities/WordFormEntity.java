package com.classicsviewer.app.database.entities;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\"\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010\b\n\u0002\b\u0016\n\u0002\u0010\u000b\n\u0002\b\u0004\b\u0087\b\u0018\u00002\u00020\u0001B=\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0003\u0012\u0006\u0010\u0005\u001a\u00020\u0003\u0012\u0006\u0010\u0006\u001a\u00020\u0007\u0012\u0006\u0010\b\u001a\u00020\u0007\u0012\u0006\u0010\t\u001a\u00020\u0007\u0012\u0006\u0010\n\u001a\u00020\u0007\u00a2\u0006\u0002\u0010\u000bJ\t\u0010\u0015\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0016\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0017\u001a\u00020\u0003H\u00c6\u0003J\t\u0010\u0018\u001a\u00020\u0007H\u00c6\u0003J\t\u0010\u0019\u001a\u00020\u0007H\u00c6\u0003J\t\u0010\u001a\u001a\u00020\u0007H\u00c6\u0003J\t\u0010\u001b\u001a\u00020\u0007H\u00c6\u0003JO\u0010\u001c\u001a\u00020\u00002\b\b\u0002\u0010\u0002\u001a\u00020\u00032\b\b\u0002\u0010\u0004\u001a\u00020\u00032\b\b\u0002\u0010\u0005\u001a\u00020\u00032\b\b\u0002\u0010\u0006\u001a\u00020\u00072\b\b\u0002\u0010\b\u001a\u00020\u00072\b\b\u0002\u0010\t\u001a\u00020\u00072\b\b\u0002\u0010\n\u001a\u00020\u0007H\u00c6\u0001J\u0013\u0010\u001d\u001a\u00020\u001e2\b\u0010\u001f\u001a\u0004\u0018\u00010\u0001H\u00d6\u0003J\t\u0010 \u001a\u00020\u0007H\u00d6\u0001J\t\u0010!\u001a\u00020\u0003H\u00d6\u0001R\u0016\u0010\u0005\u001a\u00020\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\f\u0010\rR\u0016\u0010\n\u001a\u00020\u00078\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u000e\u0010\u000fR\u0016\u0010\t\u001a\u00020\u00078\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0010\u0010\u000fR\u0016\u0010\u0006\u001a\u00020\u00078\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0011\u0010\u000fR\u0011\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0012\u0010\rR\u0016\u0010\u0004\u001a\u00020\u00038\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0013\u0010\rR\u0016\u0010\b\u001a\u00020\u00078\u0006X\u0087\u0004\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0014\u0010\u000f\u00a8\u0006\""}, d2 = {"Lcom/classicsviewer/app/database/entities/WordFormEntity;", "", "word", "", "wordNormalized", "bookId", "lineNumber", "", "wordPosition", "charStart", "charEnd", "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;IIII)V", "getBookId", "()Ljava/lang/String;", "getCharEnd", "()I", "getCharStart", "getLineNumber", "getWord", "getWordNormalized", "getWordPosition", "component1", "component2", "component3", "component4", "component5", "component6", "component7", "copy", "equals", "", "other", "hashCode", "toString", "app_debug"})
@androidx.room.Entity(tableName = "word_forms", primaryKeys = {"book_id", "line_number", "word_position"}, foreignKeys = {@androidx.room.ForeignKey(entity = com.classicsviewer.app.database.entities.BookEntity.class, parentColumns = {"id"}, childColumns = {"book_id"}, onDelete = 5)}, indices = {@androidx.room.Index(value = {"book_id", "line_number"}, name = "idx_word_forms_book_line"), @androidx.room.Index(value = {"word_normalized"}, name = "idx_word_forms_normalized")})
public final class WordFormEntity {
    @org.jetbrains.annotations.NotNull
    private final java.lang.String word = null;
    @androidx.room.ColumnInfo(name = "word_normalized")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String wordNormalized = null;
    @androidx.room.ColumnInfo(name = "book_id")
    @org.jetbrains.annotations.NotNull
    private final java.lang.String bookId = null;
    @androidx.room.ColumnInfo(name = "line_number")
    private final int lineNumber = 0;
    @androidx.room.ColumnInfo(name = "word_position")
    private final int wordPosition = 0;
    @androidx.room.ColumnInfo(name = "char_start")
    private final int charStart = 0;
    @androidx.room.ColumnInfo(name = "char_end")
    private final int charEnd = 0;
    
    public WordFormEntity(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    java.lang.String bookId, int lineNumber, int wordPosition, int charStart, int charEnd) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getWord() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getWordNormalized() {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getBookId() {
        return null;
    }
    
    public final int getLineNumber() {
        return 0;
    }
    
    public final int getWordPosition() {
        return 0;
    }
    
    public final int getCharStart() {
        return 0;
    }
    
    public final int getCharEnd() {
        return 0;
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
    
    public final int component4() {
        return 0;
    }
    
    public final int component5() {
        return 0;
    }
    
    public final int component6() {
        return 0;
    }
    
    public final int component7() {
        return 0;
    }
    
    @org.jetbrains.annotations.NotNull
    public final com.classicsviewer.app.database.entities.WordFormEntity copy(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    java.lang.String bookId, int lineNumber, int wordPosition, int charStart, int charEnd) {
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