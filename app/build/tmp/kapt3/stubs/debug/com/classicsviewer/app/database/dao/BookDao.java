package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000&\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0000\bg\u0018\u00002\u00020\u0001J\u0019\u0010\u0002\u001a\u00020\u00032\u0006\u0010\u0004\u001a\u00020\u0005H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0006J\u001b\u0010\u0007\u001a\u0004\u0018\u00010\b2\u0006\u0010\t\u001a\u00020\u0005H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0006J\u001f\u0010\n\u001a\b\u0012\u0004\u0012\u00020\b0\u000b2\u0006\u0010\u0004\u001a\u00020\u0005H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0006\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\f"}, d2 = {"Lcom/classicsviewer/app/database/dao/BookDao;", "", "getBookCountByWork", "", "workId", "", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getById", "Lcom/classicsviewer/app/database/entities/BookEntity;", "bookId", "getByWork", "", "app_debug"})
@androidx.room.Dao
public abstract interface BookDao {
    
    @androidx.room.Query(value = "SELECT * FROM books WHERE work_id = :workId ORDER BY book_number")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getByWork(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.BookEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM books WHERE id = :bookId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getById(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.database.entities.BookEntity> $completion);
    
    @androidx.room.Query(value = "SELECT COUNT(*) FROM books WHERE work_id = :workId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getBookCountByWork(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
}