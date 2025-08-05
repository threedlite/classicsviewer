package com.classicsviewer.app.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000P\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\b\u00c6\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u00042\u0006\u0010\u0006\u001a\u00020\u0007J\u0014\u0010\b\u001a\b\u0012\u0004\u0012\u00020\t0\u00042\u0006\u0010\n\u001a\u00020\u0007J\u0016\u0010\u000b\u001a\u00020\u00072\u0006\u0010\f\u001a\u00020\u00072\u0006\u0010\u0006\u001a\u00020\u0007J\u001c\u0010\r\u001a\b\u0012\u0004\u0012\u00020\u000e0\u00042\u0006\u0010\u000f\u001a\u00020\u00072\u0006\u0010\u0006\u001a\u00020\u0007J&\u0010\u0010\u001a\b\u0012\u0004\u0012\u00020\u00110\u00042\u0006\u0010\u0012\u001a\u00020\u00132\u0006\u0010\u0014\u001a\u00020\u00132\b\b\u0002\u0010\u0015\u001a\u00020\u0016J$\u0010\u0017\u001a\b\u0012\u0004\u0012\u00020\u00180\u00042\u0006\u0010\u0019\u001a\u00020\u00072\u0006\u0010\u0012\u001a\u00020\u00132\u0006\u0010\u0014\u001a\u00020\u0013J\u0014\u0010\u001a\u001a\b\u0012\u0004\u0012\u00020\u001b0\u00042\u0006\u0010\u001c\u001a\u00020\u0007\u00a8\u0006\u001d"}, d2 = {"Lcom/classicsviewer/app/data/MockDataProvider;", "", "()V", "getMockAuthors", "", "Lcom/classicsviewer/app/models/Author;", "language", "", "getMockBooks", "Lcom/classicsviewer/app/models/Book;", "workId", "getMockDictionaryEntry", "word", "getMockOccurrences", "Lcom/classicsviewer/app/models/Occurrence;", "lemma", "getMockTextLines", "Lcom/classicsviewer/app/models/TextLine;", "startLine", "", "endLine", "isGreek", "", "getMockTranslationSegments", "Lcom/classicsviewer/app/models/TranslationSegment;", "bookId", "getMockWorks", "Lcom/classicsviewer/app/models/Work;", "authorId", "app_debug"})
public final class MockDataProvider {
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.data.MockDataProvider INSTANCE = null;
    
    private MockDataProvider() {
        super();
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Author> getMockAuthors(@org.jetbrains.annotations.NotNull
    java.lang.String language) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Work> getMockWorks(@org.jetbrains.annotations.NotNull
    java.lang.String authorId) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Book> getMockBooks(@org.jetbrains.annotations.NotNull
    java.lang.String workId) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.TextLine> getMockTextLines(int startLine, int endLine, boolean isGreek) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.lang.String getMockDictionaryEntry(@org.jetbrains.annotations.NotNull
    java.lang.String word, @org.jetbrains.annotations.NotNull
    java.lang.String language) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Occurrence> getMockOccurrences(@org.jetbrains.annotations.NotNull
    java.lang.String lemma, @org.jetbrains.annotations.NotNull
    java.lang.String language) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.TranslationSegment> getMockTranslationSegments(@org.jetbrains.annotations.NotNull
    java.lang.String bookId, int startLine, int endLine) {
        return null;
    }
}