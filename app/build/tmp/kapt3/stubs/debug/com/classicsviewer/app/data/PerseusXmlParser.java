package com.classicsviewer.app.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000F\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010$\n\u0002\u0010\b\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u0012\u0010\b\u001a\u0004\u0018\u00010\t2\u0006\u0010\n\u001a\u00020\u000bH\u0002J\u0014\u0010\f\u001a\b\u0012\u0004\u0012\u00020\u000e0\r2\u0006\u0010\u000f\u001a\u00020\tJ\u001a\u0010\u0010\u001a\u000e\u0012\u0004\u0012\u00020\u0012\u0012\u0004\u0012\u00020\t0\u00112\u0006\u0010\u0013\u001a\u00020\tJ\u0012\u0010\u0014\u001a\u0004\u0018\u00010\t2\u0006\u0010\n\u001a\u00020\u000bH\u0002J\u001c\u0010\u0015\u001a\b\u0012\u0004\u0012\u00020\u00160\r2\u0006\u0010\u0017\u001a\u00020\t2\u0006\u0010\u000f\u001a\u00020\tR\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0016\u0010\u0005\u001a\n \u0007*\u0004\u0018\u00010\u00060\u0006X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0018"}, d2 = {"Lcom/classicsviewer/app/data/PerseusXmlParser;", "", "context", "Landroid/content/Context;", "(Landroid/content/Context;)V", "parserFactory", "Lorg/xmlpull/v1/XmlPullParserFactory;", "kotlin.jvm.PlatformType", "parseAuthorName", "", "inputStream", "Ljava/io/InputStream;", "parseAuthors", "", "Lcom/classicsviewer/app/models/Author;", "language", "parseTextContent", "", "", "filePath", "parseWorkTitle", "parseWorks", "Lcom/classicsviewer/app/models/Work;", "authorId", "app_debug"})
public final class PerseusXmlParser {
    @org.jetbrains.annotations.NotNull
    private final android.content.Context context = null;
    private final org.xmlpull.v1.XmlPullParserFactory parserFactory = null;
    
    public PerseusXmlParser(@org.jetbrains.annotations.NotNull
    android.content.Context context) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Author> parseAuthors(@org.jetbrains.annotations.NotNull
    java.lang.String language) {
        return null;
    }
    
    private final java.lang.String parseAuthorName(java.io.InputStream inputStream) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.List<com.classicsviewer.app.models.Work> parseWorks(@org.jetbrains.annotations.NotNull
    java.lang.String authorId, @org.jetbrains.annotations.NotNull
    java.lang.String language) {
        return null;
    }
    
    private final java.lang.String parseWorkTitle(java.io.InputStream inputStream) {
        return null;
    }
    
    @org.jetbrains.annotations.NotNull
    public final java.util.Map<java.lang.Integer, java.lang.String> parseTextContent(@org.jetbrains.annotations.NotNull
    java.lang.String filePath) {
        return null;
    }
}