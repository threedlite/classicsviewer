package com.classicsviewer.app.database.dao;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u001c\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0007\bg\u0018\u00002\u00020\u0001J\'\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u00032\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\bJ\'\u0010\t\u001a\b\u0012\u0004\u0012\u00020\u00060\u00032\u0006\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\bJ\u001b\u0010\n\u001a\u0004\u0018\u00010\u00062\u0006\u0010\u0007\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u000bJ\u001b\u0010\f\u001a\u0004\u0018\u00010\u00042\u0006\u0010\u0007\u001a\u00020\u0006H\u00a7@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\u000b\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006\r"}, d2 = {"Lcom/classicsviewer/app/database/dao/LemmaMapDao;", "", "getAllLemmaMappingsForWord", "", "Lcom/classicsviewer/app/database/entities/LemmaMapEntity;", "wordForm", "", "wordNormalized", "(Ljava/lang/String;Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getAllLemmasForWord", "getLemmaForWord", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getLemmaMapEntry", "app_debug"})
@androidx.room.Dao
public abstract interface LemmaMapDao {
    
    @androidx.room.Query(value = "SELECT lemma FROM lemma_map WHERE word_normalized = :wordNormalized ORDER BY confidence DESC LIMIT 1")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getLemmaForWord(@org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.String> $completion);
    
    @androidx.room.Query(value = "SELECT DISTINCT lemma FROM lemma_map WHERE word_form = :wordForm OR word_normalized = :wordNormalized ORDER BY confidence DESC")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getAllLemmasForWord(@org.jetbrains.annotations.NotNull
    java.lang.String wordForm, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<java.lang.String>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM lemma_map WHERE word_form = :wordForm OR word_normalized = :wordNormalized ORDER BY confidence DESC")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getAllLemmaMappingsForWord(@org.jetbrains.annotations.NotNull
    java.lang.String wordForm, @org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.database.entities.LemmaMapEntity>> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM lemma_map WHERE word_normalized = :wordNormalized ORDER BY confidence DESC LIMIT 1")
    @org.jetbrains.annotations.Nullable
    public abstract java.lang.Object getLemmaMapEntry(@org.jetbrains.annotations.NotNull
    java.lang.String wordNormalized, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.database.entities.LemmaMapEntity> $completion);
}