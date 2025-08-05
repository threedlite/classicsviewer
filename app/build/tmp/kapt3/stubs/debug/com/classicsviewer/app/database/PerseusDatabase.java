package com.classicsviewer.app.database;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000D\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\b\'\u0018\u0000 \u00152\u00020\u0001:\u0001\u0015B\u0005\u00a2\u0006\u0002\u0010\u0002J\b\u0010\u0003\u001a\u00020\u0004H&J\b\u0010\u0005\u001a\u00020\u0006H&J\b\u0010\u0007\u001a\u00020\bH&J\b\u0010\t\u001a\u00020\nH&J\b\u0010\u000b\u001a\u00020\fH&J\b\u0010\r\u001a\u00020\u000eH&J\b\u0010\u000f\u001a\u00020\u0010H&J\b\u0010\u0011\u001a\u00020\u0012H&J\b\u0010\u0013\u001a\u00020\u0014H&\u00a8\u0006\u0016"}, d2 = {"Lcom/classicsviewer/app/database/PerseusDatabase;", "Landroidx/room/RoomDatabase;", "()V", "authorDao", "Lcom/classicsviewer/app/database/dao/AuthorDao;", "bookDao", "Lcom/classicsviewer/app/database/dao/BookDao;", "dictionaryDao", "Lcom/classicsviewer/app/database/dao/DictionaryDao;", "lemmaDao", "Lcom/classicsviewer/app/database/dao/LemmaDao;", "lemmaMapDao", "Lcom/classicsviewer/app/database/dao/LemmaMapDao;", "textLineDao", "Lcom/classicsviewer/app/database/dao/TextLineDao;", "translationSegmentDao", "Lcom/classicsviewer/app/database/dao/TranslationSegmentDao;", "wordFormDao", "Lcom/classicsviewer/app/database/dao/WordFormDao;", "workDao", "Lcom/classicsviewer/app/database/dao/WorkDao;", "Companion", "app_debug"})
@androidx.room.Database(entities = {com.classicsviewer.app.database.entities.AuthorEntity.class, com.classicsviewer.app.database.entities.WorkEntity.class, com.classicsviewer.app.database.entities.BookEntity.class, com.classicsviewer.app.database.entities.TextLineEntity.class, com.classicsviewer.app.database.entities.WordFormEntity.class, com.classicsviewer.app.database.entities.LemmaMapEntity.class, com.classicsviewer.app.database.entities.DictionaryEntity.class, com.classicsviewer.app.database.entities.TranslationSegmentEntity.class}, version = 2, exportSchema = false)
public abstract class PerseusDatabase extends androidx.room.RoomDatabase {
    @kotlin.jvm.Volatile
    @org.jetbrains.annotations.Nullable
    private static volatile com.classicsviewer.app.database.PerseusDatabase INSTANCE;
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.database.PerseusDatabase.Companion Companion = null;
    
    public PerseusDatabase() {
        super();
    }
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.AuthorDao authorDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.WorkDao workDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.BookDao bookDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.TextLineDao textLineDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.WordFormDao wordFormDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.LemmaDao lemmaDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.LemmaMapDao lemmaMapDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.DictionaryDao dictionaryDao();
    
    @org.jetbrains.annotations.NotNull
    public abstract com.classicsviewer.app.database.dao.TranslationSegmentDao translationSegmentDao();
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000 \n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\b\u0086\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002J\u0010\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\bH\u0002J\u0006\u0010\t\u001a\u00020\u0006J\u000e\u0010\n\u001a\u00020\u00042\u0006\u0010\u0007\u001a\u00020\bR\u0010\u0010\u0003\u001a\u0004\u0018\u00010\u0004X\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u000b"}, d2 = {"Lcom/classicsviewer/app/database/PerseusDatabase$Companion;", "", "()V", "INSTANCE", "Lcom/classicsviewer/app/database/PerseusDatabase;", "checkAndExtractFromObb", "", "context", "Landroid/content/Context;", "destroyInstance", "getInstance", "app_debug"})
    public static final class Companion {
        
        private Companion() {
            super();
        }
        
        @org.jetbrains.annotations.NotNull
        public final com.classicsviewer.app.database.PerseusDatabase getInstance(@org.jetbrains.annotations.NotNull
        android.content.Context context) {
            return null;
        }
        
        public final void destroyInstance() {
        }
        
        private final void checkAndExtractFromObb(android.content.Context context) {
        }
    }
}