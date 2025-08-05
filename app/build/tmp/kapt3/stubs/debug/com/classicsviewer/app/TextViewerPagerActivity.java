package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000T\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010 \n\u0002\u0010\u000e\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010$\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0006\u0018\u00002\u00020\u0001:\u0001#B\u0005\u00a2\u0006\u0002\u0010\u0002J\b\u0010\u0018\u001a\u00020\u0019H\u0002J\b\u0010\u001a\u001a\u00020\u0019H\u0002J\b\u0010\u001b\u001a\u00020\u0019H\u0002J\u0012\u0010\u001c\u001a\u00020\u00192\b\u0010\u001d\u001a\u0004\u0018\u00010\u001eH\u0014J\u0010\u0010\u001f\u001a\u00020\u00192\u0006\u0010 \u001a\u00020\u0005H\u0002J\b\u0010!\u001a\u00020\u0019H\u0002J\b\u0010\"\u001a\u00020\u0019H\u0002R\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\u0005X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\t\u001a\u00020\u0005X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\n\u001a\u00020\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\f\u001a\u00020\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0014\u0010\r\u001a\b\u0012\u0004\u0012\u00020\u000e0\u0004X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u000f\u001a\u00020\u0005X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0010\u001a\u00020\u0011X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0012\u001a\u00020\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0013\u001a\b\u0012\u0004\u0012\u00020\u00140\u0004X\u0082\u000e\u00a2\u0006\u0002\n\u0000R \u0010\u0015\u001a\u0014\u0012\u0004\u0012\u00020\u0005\u0012\n\u0012\b\u0012\u0004\u0012\u00020\u00140\u00040\u0016X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0017\u001a\u00020\u0005X\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006$"}, d2 = {"Lcom/classicsviewer/app/TextViewerPagerActivity;", "Lcom/classicsviewer/app/BaseActivity;", "()V", "availableTranslators", "", "", "binding", "Lcom/classicsviewer/app/databinding/ActivityTextViewerPagerBinding;", "bookId", "bookNumber", "currentEndLine", "", "currentStartLine", "greekLines", "Lcom/classicsviewer/app/models/TextLine;", "language", "repository", "Lcom/classicsviewer/app/data/DataRepository;", "totalLines", "translationSegments", "Lcom/classicsviewer/app/models/TranslationSegment;", "translationsByTranslator", "", "workId", "loadTexts", "", "navigateToNextPage", "navigateToPreviousPage", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "openDictionary", "word", "setupEdgeToEdgeExclusions", "updateNavigationButtons", "TextPagerAdapter", "app_debug"})
public final class TextViewerPagerActivity extends com.classicsviewer.app.BaseActivity {
    private com.classicsviewer.app.databinding.ActivityTextViewerPagerBinding binding;
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
    @org.jetbrains.annotations.NotNull
    private java.util.List<com.classicsviewer.app.models.TextLine> greekLines;
    @org.jetbrains.annotations.NotNull
    private java.util.List<com.classicsviewer.app.models.TranslationSegment> translationSegments;
    @org.jetbrains.annotations.NotNull
    private java.util.List<java.lang.String> availableTranslators;
    @org.jetbrains.annotations.NotNull
    private java.util.Map<java.lang.String, ? extends java.util.List<com.classicsviewer.app.models.TranslationSegment>> translationsByTranslator;
    
    public TextViewerPagerActivity() {
        super();
    }
    
    @java.lang.Override
    protected void onCreate(@org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
    }
    
    private final void setupEdgeToEdgeExclusions() {
    }
    
    private final void loadTexts() {
    }
    
    private final void navigateToPreviousPage() {
    }
    
    private final void navigateToNextPage() {
    }
    
    private final void updateNavigationButtons() {
    }
    
    private final void openDictionary(java.lang.String word) {
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000 \n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0002\b\u0002\b\u0082\u0004\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u0010\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\bH\u0016J\b\u0010\t\u001a\u00020\bH\u0016\u00a8\u0006\n"}, d2 = {"Lcom/classicsviewer/app/TextViewerPagerActivity$TextPagerAdapter;", "Landroidx/viewpager2/adapter/FragmentStateAdapter;", "fa", "Landroidx/fragment/app/FragmentActivity;", "(Lcom/classicsviewer/app/TextViewerPagerActivity;Landroidx/fragment/app/FragmentActivity;)V", "createFragment", "Landroidx/fragment/app/Fragment;", "position", "", "getItemCount", "app_debug"})
    final class TextPagerAdapter extends androidx.viewpager2.adapter.FragmentStateAdapter {
        
        public TextPagerAdapter(@org.jetbrains.annotations.NotNull
        androidx.fragment.app.FragmentActivity fa) {
            super(null);
        }
        
        @java.lang.Override
        public int getItemCount() {
            return 0;
        }
        
        @java.lang.Override
        @org.jetbrains.annotations.NotNull
        public androidx.fragment.app.Fragment createFragment(int position) {
            return null;
        }
    }
}