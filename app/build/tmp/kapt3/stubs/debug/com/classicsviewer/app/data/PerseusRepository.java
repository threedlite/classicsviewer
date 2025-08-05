package com.classicsviewer.app.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u00b2\u0001\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J!\u0010\u001b\u001a\u00020\u001c2\u0006\u0010\u001d\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J!\u0010!\u001a\u00020\"2\u0006\u0010#\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J\u001f\u0010$\u001a\b\u0012\u0004\u0012\u00020&0%2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\'J\u001f\u0010(\u001a\b\u0012\u0004\u0012\u00020\u001e0%2\u0006\u0010)\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\'J\u001f\u0010*\u001a\b\u0012\u0004\u0012\u00020+0%2\u0006\u0010,\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010\'J#\u0010-\u001a\u0004\u0018\u00010\u001e2\u0006\u0010#\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J#\u0010.\u001a\u0004\u0018\u00010/2\u0006\u0010#\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J#\u00100\u001a\u0004\u0018\u00010\u001e2\u0006\u0010#\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J\'\u00101\u001a\b\u0012\u0004\u0012\u0002020%2\u0006\u0010\u001d\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J7\u00103\u001a\b\u0012\u0004\u0012\u0002040%2\u0006\u0010,\u001a\u00020\u001e2\u0006\u0010)\u001a\u00020\u001e2\u0006\u00105\u001a\u00020\u001c2\u0006\u00106\u001a\u00020\u001cH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u00107J/\u00108\u001a\b\u0012\u0004\u0012\u0002090%2\u0006\u0010)\u001a\u00020\u001e2\u0006\u00105\u001a\u00020\u001c2\u0006\u00106\u001a\u00020\u001cH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010:J7\u0010;\u001a\b\u0012\u0004\u0012\u0002090%2\u0006\u0010)\u001a\u00020\u001e2\u0006\u0010<\u001a\u00020\u001e2\u0006\u00105\u001a\u00020\u001c2\u0006\u00106\u001a\u00020\u001cH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u00107J\'\u0010=\u001a\b\u0012\u0004\u0012\u00020>0%2\u0006\u0010?\u001a\u00020\u001e2\u0006\u0010\u001f\u001a\u00020\u001eH\u0096@\u00f8\u0001\u0000\u00a2\u0006\u0002\u0010 J\u0010\u0010@\u001a\u00020\u001e2\u0006\u0010#\u001a\u00020\u001eH\u0002J$\u0010A\u001a\b\u0012\u0004\u0012\u00020B0%2\u0006\u0010C\u001a\u00020\u001e2\f\u0010D\u001a\b\u0012\u0004\u0012\u00020E0%H\u0002R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0007\u001a\u00020\bX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\t\u001a\u00020\nX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000b\u001a\u00020\fX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\r\u001a\u00020\u000eX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000f\u001a\u00020\u0010X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0011\u001a\u00020\u0012X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0013\u001a\u00020\u0014X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0015\u001a\u00020\u0016X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0017\u001a\u00020\u0018X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0019\u001a\u00020\u001aX\u0082\u0004\u00a2\u0006\u0002\n\u0000\u0082\u0002\u0004\n\u0002\b\u0019\u00a8\u0006F"}, d2 = {"Lcom/classicsviewer/app/data/PerseusRepository;", "Lcom/classicsviewer/app/data/DataRepository;", "context", "Landroid/content/Context;", "(Landroid/content/Context;)V", "authorDao", "Lcom/classicsviewer/app/database/dao/AuthorDao;", "bookDao", "Lcom/classicsviewer/app/database/dao/BookDao;", "database", "Lcom/classicsviewer/app/database/PerseusDatabase;", "dictionaryDao", "Lcom/classicsviewer/app/database/dao/DictionaryDao;", "greekLemmatizer", "Lcom/classicsviewer/app/lemmatization/GreekLemmatizer;", "lemmaDao", "Lcom/classicsviewer/app/database/dao/LemmaDao;", "lemmaMapDao", "Lcom/classicsviewer/app/database/dao/LemmaMapDao;", "textLineDao", "Lcom/classicsviewer/app/database/dao/TextLineDao;", "translationSegmentDao", "Lcom/classicsviewer/app/database/dao/TranslationSegmentDao;", "wordFormDao", "Lcom/classicsviewer/app/database/dao/WordFormDao;", "workDao", "Lcom/classicsviewer/app/database/dao/WorkDao;", "countLemmaOccurrences", "", "lemma", "", "language", "(Ljava/lang/String;Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getAllDictionaryEntries", "Lcom/classicsviewer/app/data/DictionaryResultMultiple;", "word", "getAuthors", "", "Lcom/classicsviewer/app/models/Author;", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getAvailableTranslators", "bookId", "getBooks", "Lcom/classicsviewer/app/models/Book;", "workId", "getDictionaryEntry", "getDictionaryEntryWithMorphology", "Lcom/classicsviewer/app/data/DictionaryResult;", "getLemmaForWord", "getLemmaOccurrences", "Lcom/classicsviewer/app/models/Occurrence;", "getTextLines", "Lcom/classicsviewer/app/models/TextLine;", "startLine", "endLine", "(Ljava/lang/String;Ljava/lang/String;IILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getTranslationSegments", "Lcom/classicsviewer/app/models/TranslationSegment;", "(Ljava/lang/String;IILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "getTranslationSegmentsByTranslator", "translator", "getWorks", "Lcom/classicsviewer/app/models/Work;", "authorId", "normalizeGreek", "parseWordsFromLine", "Lcom/classicsviewer/app/models/Word;", "lineText", "wordForms", "Lcom/classicsviewer/app/database/entities/WordFormEntity;", "app_debug"})
public final class PerseusRepository implements com.classicsviewer.app.data.DataRepository {
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.PerseusDatabase database = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.AuthorDao authorDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.WorkDao workDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.BookDao bookDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.TextLineDao textLineDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.WordFormDao wordFormDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.LemmaDao lemmaDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.LemmaMapDao lemmaMapDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.DictionaryDao dictionaryDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.database.dao.TranslationSegmentDao translationSegmentDao = null;
    @org.jetbrains.annotations.NotNull
    private final com.classicsviewer.app.lemmatization.GreekLemmatizer greekLemmatizer = null;
    
    public PerseusRepository(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        super();
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getAuthors(@org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.Author>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getWorks(@org.jetbrains.annotations.NotNull
    java.lang.String authorId, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.Work>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getBooks(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.Book>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getTextLines(@org.jetbrains.annotations.NotNull
    java.lang.String workId, @org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.TextLine>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getAllDictionaryEntries(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.data.DictionaryResultMultiple> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getDictionaryEntryWithMorphology(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super com.classicsviewer.app.data.DictionaryResult> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getDictionaryEntry(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.String> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getLemmaOccurrences(@org.jetbrains.annotations.NotNull
    java.lang.String lemma, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.Occurrence>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object countLemmaOccurrences(@org.jetbrains.annotations.NotNull
    java.lang.String lemma, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.Integer> $completion) {
        return null;
    }
    
    private final java.util.List<com.classicsviewer.app.models.Word> parseWordsFromLine(java.lang.String lineText, java.util.List<com.classicsviewer.app.database.entities.WordFormEntity> wordForms) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getTranslationSegments(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.TranslationSegment>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getAvailableTranslators(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<java.lang.String>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getTranslationSegmentsByTranslator(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, @org.jetbrains.annotations.NotNull
    java.lang.String translator, int startLine, int endLine, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.util.List<com.classicsviewer.app.models.TranslationSegment>> $completion) {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.Nullable
    public java.lang.Object getLemmaForWord(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String language, @org.jetbrains.annotations.NotNull
    kotlin.coroutines.Continuation<? super java.lang.String> $completion) {
        return null;
    }
    
    private final java.lang.String normalizeGreek(java.lang.String word) {
        return null;
    }
}