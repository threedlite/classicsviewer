package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\"\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0004\n\u0002\u0010\b\n\u0000\bg\u0018\u00002\u00020\u0001J\u001f\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u001b\u0010\b\u001a\u0004\u0018\u00010\u00042\u0006\u0010\t\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007J\u0019\u0010\n\u001a\u00020\u000b2\u0006\u0010\u0005\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0007\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\f"}, d2 = {"Lcom/classicsviewer/app/database/dao/WorkDao;", "", "getByAuthor", "", "Lcom/classicsviewer/app/database/entities/WorkEntity;", "authorId", "", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getById", "workId", "getWorkCountByAuthor", "", "app_debug"})
@androidx.room.Dao
public abstract interface WorkDao {
    
    @androidx.room.Query(value = "SELECT * FROM works WHERE author_id = :authorId ORDER BY title")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getByAuthor(@org.jetbrains.annotations.NotNull
    java.lang.String authorId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.WorkEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM works WHERE id = :workId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getById(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.database.entities.WorkEntity> $completion);
    
    @androidx.room.Query(value = "SELECT COUNT(*) FROM works WHERE author_id = :authorId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getWorkCountByAuthor(@org.jetbrains.annotations.NotNull
    java.lang.String authorId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion);
}