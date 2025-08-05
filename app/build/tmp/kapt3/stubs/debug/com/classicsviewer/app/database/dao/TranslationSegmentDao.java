package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000,\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0010\b\n\u0002\b\b\n\u0002\u0010\u000b\n\u0002\b\u0002\bg\u0018\u00002\u00020\u0001J\u001f\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u001f\u0010\b\u001a\b\u0012\u0004\u0012\u00020\u00060\u00032\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u0019\u0010\t\u001a\u00020\n2\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J/\u0010\u000b\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\f\u001a\u00020\n2\u0006\u0010\r\u001a\u00020\nH\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u000eJ7\u0010\u000f\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0010\u001a\u00020\u00062\u0006\u0010\f\u001a\u00020\n2\u0006\u0010\r\u001a\u00020\nH\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0011J\u0019\u0010\u0012\u001a\u00020\u00132\u0006\u0010\u0014\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\u0015"}, d2 = {"Lcom/classicsviewer/app/database/dao/TranslationSegmentDao;", "", "getAllTranslationSegments", "", "Lcom/classicsviewer/app/database/entities/TranslationSegmentEntity;", "bookId", "", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getAvailableTranslators", "getTranslationCount", "", "getTranslationSegments", "startLine", "endLine", "(Ljava/lang/String;IILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getTranslationSegmentsByTranslator", "translator", "(Ljava/lang/String;Ljava/lang/String;IILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "hasTranslationsForWork", "", "workId", "app_debug"})
@androidx.room.Dao
public abstract interface TranslationSegmentDao {
    
    @androidx.room.Query(value = "\n        SELECT * FROM translation_segments \n        WHERE book_id = :bookId \n        AND start_line <= :endLine \n        AND (end_line IS NULL OR end_line >= :startLine)\n        ORDER BY start_line\n    ")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getTranslationSegments(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.TranslationSegmentEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM translation_segments WHERE book_id = :bookId ORDER BY start_line")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getAllTranslationSegments(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.TranslationSegmentEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT COUNT(*) FROM translation_segments WHERE book_id = :bookId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getTranslationCount(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
    
    @androidx.room.Query(value = "SELECT DISTINCT translator FROM translation_segments WHERE book_id = :bookId AND translator IS NOT NULL ORDER BY translator")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getAvailableTranslators(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<java.lang.String>> $completion);
    
    @androidx.room.Query(value = "\n        SELECT * FROM translation_segments \n        WHERE book_id = :bookId \n        AND translator = :translator\n        AND start_line <= :endLine \n        AND (end_line IS NULL OR end_line >= :startLine)\n        ORDER BY start_line\n    ")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getTranslationSegmentsByTranslator(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    java.lang.String translator, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.TranslationSegmentEntity>> $completion);
    
    @androidx.room.Query(value = "\n        SELECT EXISTS(\n            SELECT 1 FROM translation_segments ts \n            JOIN books b ON ts.book_id = b.id \n            WHERE b.work_id = :workId\n        )\n    ")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object hasTranslationsForWork(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Boolean> $completion);
}