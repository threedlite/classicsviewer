package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000$\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010\b\n\u0002\b\u0006\bg\u0018\u00002\u00020\u0001J\u001f\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J/\u0010\b\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\t\u001a\u00020\n2\u0006\u0010\u000b\u001a\u00020\nH\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\fJ\u001b\u0010\r\u001a\u0004\u0018\u00010\n2\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u001b\u0010\u000e\u001a\u0004\u0018\u00010\n2\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u0019\u0010\u000f\u001a\u00020\n2\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\u0010"}, d2 = {"Lcom/classicsviewer/app/database/dao/TextLineDao;", "", "getByBook", "", "Lcom/classicsviewer/app/database/entities/TextLineEntity;", "bookId", "", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getByBookAndRange", "startLine", "", "endLine", "(Ljava/lang/String;IILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getFirstLineNumber", "getLastLineNumber", "getLineCountByBook", "app_debug"})
@androidx.room.Dao
public abstract interface TextLineDao {
    
    @androidx.room.Query(value = "SELECT * FROM text_lines WHERE book_id = :bookId ORDER BY line_number")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getByBook(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.TextLineEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM text_lines WHERE book_id = :bookId AND line_number >= :startLine AND line_number <= :endLine ORDER BY line_number")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getByBookAndRange(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.TextLineEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT COUNT(*) FROM text_lines WHERE book_id = :bookId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getLineCountByBook(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
    
    @androidx.room.Query(value = "SELECT MIN(line_number) FROM text_lines WHERE book_id = :bookId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getFirstLineNumber(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
    
    @androidx.room.Query(value = "SELECT MAX(line_number) FROM text_lines WHERE book_id = :bookId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getLastLineNumber(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
}