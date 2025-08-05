package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000.\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0002\b\u0006\n\u0002\u0018\u0002\n\u0000\u0018\u00002\u00020\u0001B\u0005\u00a2\u0006\u0002\u0010\u0002J\u0010\u0010\u0007\u001a\u00020\b2\u0006\u0010\t\u001a\u00020\bH\u0002J(\u0010\n\u001a\u00020\u000b2\u0006\u0010\f\u001a\u00020\b2\u0006\u0010\r\u001a\u00020\b2\u0006\u0010\u000e\u001a\u00020\b2\u0006\u0010\u000f\u001a\u00020\bH\u0002J\u0012\u0010\u0010\u001a\u00020\u000b2\b\u0010\u0011\u001a\u0004\u0018\u00010\u0012H\u0014R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082.\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0006X\u0082.\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0013"}, d2 = {"Lcom/classicsviewer/app/DictionaryActivity;", "Lcom/classicsviewer/app/BaseActivity;", "()V", "binding", "Lcom/classicsviewer/app/databinding/ActivityDictionaryBinding;", "repository", "Lcom/classicsviewer/app/data/DataRepository;", "formatMorphInfo", "", "morphInfo", "loadDefinition", "", "lemma", "language", "originalWord", "displayWord", "onCreate", "savedInstanceState", "Landroid/os/Bundle;", "app_debug"})
public final class DictionaryActivity extends com.classicsviewer.app.BaseActivity {
    private com.classicsviewer.app.databinding.ActivityDictionaryBinding binding;
    private com.classicsviewer.app.data.DataRepository repository;
    
    public DictionaryActivity() {
        super();
    }
    
    @java.lang.Override
    protected void onCreate(@org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
    }
    
    private final void loadDefinition(java.lang.String lemma, java.lang.String language, java.lang.String originalWord, java.lang.String displayWord) {
    }
    
    private final java.lang.String formatMorphInfo(java.lang.String morphInfo) {
        return null;
    }
}