package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000:\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\b\u0010\u0010\u001a\u00020\u0011H\u0002J\b\u0010\u0012\u001a\u00020\u0011H\u0002J\b\u0010\u0013\u001a\u00020\u0011H\u0002J\u0012\u0010\u0014\u001a\u00020\u00112\b\u0010\u0015\u001a\u0004\u0018\u00010\u0016H\u0014J\u0010\u0010\u0017\u001a\u00020\u00112\u0006\u0010\u0018\u001a\u00020\u0006H\u0002J\b\u0010\u0019\u001a\u00020\u0011H\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0007\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\n\u001a\u00020\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000b\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\f\u001a\u00020\rX\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000e\u001a\u00020\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000f\u001a\u00020\u0006X\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u001a"}, d2 = {"Lcom/classicsviewer/app/TextViewerActivity;", "Lcom/classicsviewer/app/BaseActivity;", "()V", "binding", "Lcom/classicsviewer/app/databinding/ActivityTextViewerBinding;", "bookId", "", "bookNumber", "currentEndLine", "", "currentStartLine", "language", "repository", "Lcom/classicsviewer/app/data/DataRepository;", "totalLines", "workId", "loadText", "", "navigateToNextPage", "navigateToPreviousPage", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "openDictionary", "word", "updateNavigationButtons", "app_debug"})
public final class TextViewerActivity extends com.classicsviewer.app.BaseActivity {
    private com.classicsviewer.app.databinding.ActivityTextViewerBinding binding;
    private com.classicsviewer.app.data.DataRepository repository;
    @org.jetbrains.annotations.NotNull
    private java.lang.String workId = "";
    @org.jetbrains.annotations.NotNull
    private java.lang.String bookId = "";
    @org.jetbrains.annotations.NotNull
    private java.lang.String bookNumber = "";
    private int currentStartLine = 1;
    private int currentEndLine = 100;
    private int totalLines = 100;
    @org.jetbrains.annotations.NotNull
    private java.lang.String language = "";
    
    public TextViewerActivity() {
        super();
    }
    
    @java.lang.Override
    protected void onCreate(@org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
    }
    
    private final void loadText() {
    }
    
    private final void openDictionary(java.lang.String word) {
    }
    
    private final void navigateToPreviousPage() {
    }
    
    private final void navigateToNextPage() {
    }
    
    private final void updateNavigationButtons() {
    }
}