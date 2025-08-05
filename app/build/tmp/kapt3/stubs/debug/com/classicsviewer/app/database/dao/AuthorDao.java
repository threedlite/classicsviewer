package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u001e\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010 \n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0005\bg\u0018\u00002\u00020\u0001J\u0017\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u0003H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u0005J\u001b\u0010\u0006\u001a\u0004\u0018\u00010\u00072\u0006\u0010\b\u001a\u00020\u0004H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\tJ\u001f\u0010\n\u001a\b\u0012\u0004\u0012\u00020\u00070\u00032\u0006\u0010\u000b\u001a\u00020\u0004H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\t\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\f"}, d2 = {"Lcom/classicsviewer/app/database/dao/AuthorDao;", "", "getAllLanguages", "", "", "(Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getById", "Lcom/classicsviewer/app/database/entities/AuthorEntity;", "authorId", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getByLanguage", "language", "app_debug"})
@androidx.room.Dao
public abstract interface AuthorDao {
    
    @androidx.room.Query(value = "SELECT * FROM authors WHERE language = :language ORDER BY name")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getByLanguage(@org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.AuthorEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM authors WHERE id = :authorId")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getById(@org.jetbrains.annotations.NotNull
    java.lang.String authorId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.database.entities.AuthorEntity> $completion);
    
    @androidx.room.Query(value = "SELECT DISTINCT language FROM authors")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getAllLanguages(@org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<java.lang.String>> $completion);
}