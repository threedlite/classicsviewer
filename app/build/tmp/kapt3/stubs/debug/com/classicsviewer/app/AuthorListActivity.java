package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00004\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0003\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\u0010\u0010\u0007\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\nH\u0002J\b\u0010\u000b\u001a\u00020\fH\u0002J\u0012\u0010\r\u001a\u00020\b2\b\u0010\u000e\u001a\u0004\u0018\u00010\u000fH\u0014J\b\u0010\u0010\u001a\u00020\bH\u0014J\b\u0010\u0011\u001a\u00020\bH\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082.\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0012"}, d2 = {"Lcom/classicsviewer/app/AuthorListActivity;", "Lcom/classicsviewer/app/BaseActivity;", "()V", "binding", "Lcom/classicsviewer/app/databinding/ActivityListBinding;", "repository", "Lcom/classicsviewer/app/data/DataRepository;", "loadAuthors", "", "language", "", "needsDatabaseExtraction", "", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "onResume", "setupAfterDatabaseReady", "app_debug"})
public final class AuthorListActivity extends com.classicsviewer.app.BaseActivity {
    private com.classicsviewer.app.databinding.ActivityListBinding binding;
    private com.classicsviewer.app.data.DataRepository repository;
    
    public AuthorListActivity() {
        super();
    }
    
    @java.lang.Override
    protected void onCreate(@org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
    }
    
    private final void loadAuthors(java.lang.String language) {
    }
    
    @java.lang.Override
    protected void onResume() {
    }
    
    private final boolean needsDatabaseExtraction() {
        return false;
    }
    
    private final void setupAfterDatabaseReady() {
    }
}