package com.classicsviewer.app.fragments;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000V\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0010\u000b\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0006\u0018\u0000 !2\u00020\u0001:\u0002!\"B\u0005\u00a2\u0006\u0002\u0010\u0002J\b\u0010\u0015\u001a\u00020\u0011H\u0002J$\u0010\u0016\u001a\u00020\u00172\u0006\u0010\u0018\u001a\u00020\u00192\b\u0010\u001a\u001a\u0004\u0018\u00010\u001b2\b\u0010\u001c\u001a\u0004\u0018\u00010\u001dH\u0016J\b\u0010\u001e\u001a\u00020\u0011H\u0016J\u001a\u0010\u001f\u001a\u00020\u00112\u0006\u0010 \u001a\u00020\u00172\b\u0010\u001c\u001a\u0004\u0018\u00010\u001dH\u0016R\u0010\u0010\u0003\u001a\u0004\u0018\u00010\u0004X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0005\u001a\u00020\u00048BX\u0082\u0004\u00a2\u0006\u0006\u001a\u0004\b\u0006\u0010\u0007R\u000e\u0010\b\u001a\u00020\tX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u000e\u0010\n\u001a\u00020\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0016\u0010\f\u001a\n\u0012\u0004\u0012\u00020\u000e\u0018\u00010\rX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u001c\u0010\u000f\u001a\u0010\u0012\u0004\u0012\u00020\u000b\u0012\u0004\u0012\u00020\u0011\u0018\u00010\u0010X\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0016\u0010\u0012\u001a\n\u0012\u0004\u0012\u00020\u0013\u0018\u00010\rX\u0082\u000e\u00a2\u0006\u0002\n\u0000R\u0010\u0010\u0014\u001a\u0004\u0018\u00010\u000bX\u0082\u000e\u00a2\u0006\u0002\n\u0000\u00a8\u0006#"}, d2 = {"Lcom/classicsviewer/app/fragments/TextPageFragment;", "Landroidx/fragment/app/Fragment;", "()V", "_binding", "Lcom/classicsviewer/app/databinding/FragmentTextPageBinding;", "binding", "getBinding", "()Lcom/classicsviewer/app/databinding/FragmentTextPageBinding;", "isGreek", "", "language", "", "lines", "", "Lcom/classicsviewer/app/models/TextLine;", "onWordClick", "Lkotlin/Function1;", "", "translationSegments", "Lcom/classicsviewer/app/models/TranslationSegment;", "translator", "displayTranslations", "onCreateView", "Landroid/view/View;", "inflater", "Landroid/view/LayoutInflater;", "container", "Landroid/view/ViewGroup;", "savedInstanceState", "Landroid/os/Bundle;", "onDestroyView", "onViewCreated", "view", "Companion", "OnWordClickListener", "app_debug"})
public final class TextPageFragment extends androidx.fragment.app.Fragment {
    @org.jetbrains.annotations.Nullable
    private com.classicsviewer.app.databinding.FragmentTextPageBinding _binding;
    @org.jetbrains.annotations.Nullable
    private java.util.List<com.classicsviewer.app.models.TextLine> lines;
    @org.jetbrains.annotations.NotNull
    private java.lang.String language = "";
    private boolean isGreek = true;
    @org.jetbrains.annotations.Nullable
    private kotlin.jvm.functions.Function1<? super java.lang.String, kotlin.Unit> onWordClick;
    @org.jetbrains.annotations.Nullable
    private java.util.List<com.classicsviewer.app.models.TranslationSegment> translationSegments;
    @org.jetbrains.annotations.Nullable
    private java.lang.String translator;
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String ARG_LANGUAGE = "language";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String ARG_IS_GREEK = "is_greek";
    @org.jetbrains.annotations.NotNull
    private static final java.lang.String ARG_TRANSLATOR = "translator";
    @org.jetbrains.annotations.NotNull
    public static final com.classicsviewer.app.fragments.TextPageFragment.Companion Companion = null;
    
    public TextPageFragment() {
        super();
    }
    
    private final com.classicsviewer.app.databinding.FragmentTextPageBinding getBinding() {
        return null;
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.NotNull
    public android.view.View onCreateView(@org.jetbrains.annotations.NotNull
    android.view.LayoutInflater inflater, @org.jetbrains.annotations.Nullable
    android.view.ViewGroup container, @org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
        return null;
    }
    
    @java.lang.Override
    public void onViewCreated(@org.jetbrains.annotations.NotNull
    android.view.View view, @org.jetbrains.annotations.Nullable
    android.os.Bundle savedInstanceState) {
    }
    
    private final void displayTranslations() {
    }
    
    @java.lang.Override
    public void onDestroyView() {
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\b\u0086\u0003\u0018\u00002\u00020\u0001B\u0007\b\u0002\u00a2\u0006\u0002\u0010\u0002JV\u0010\u0007\u001a\u00020\b2\f\u0010\t\u001a\b\u0012\u0004\u0012\u00020\u000b0\n2\u0006\u0010\f\u001a\u00020\u00042\u0006\u0010\r\u001a\u00020\u000e2\u0012\u0010\u000f\u001a\u000e\u0012\u0004\u0012\u00020\u0004\u0012\u0004\u0012\u00020\u00110\u00102\u0010\b\u0002\u0010\u0012\u001a\n\u0012\u0004\u0012\u00020\u0013\u0018\u00010\n2\n\b\u0002\u0010\u0014\u001a\u0004\u0018\u00010\u0004R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0005\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0004X\u0082T\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0015"}, d2 = {"Lcom/classicsviewer/app/fragments/TextPageFragment$Companion;", "", "()V", "ARG_IS_GREEK", "", "ARG_LANGUAGE", "ARG_TRANSLATOR", "newInstance", "Lcom/classicsviewer/app/fragments/TextPageFragment;", "lines", "", "Lcom/classicsviewer/app/models/TextLine;", "language", "isGreek", "", "onWordClick", "Lkotlin/Function1;", "", "translationSegments", "Lcom/classicsviewer/app/models/TranslationSegment;", "translator", "app_debug"})
    public static final class Companion {
        
        private Companion() {
            super();
        }
        
        @org.jetbrains.annotations.NotNull
        public final com.classicsviewer.app.fragments.TextPageFragment newInstance(@org.jetbrains.annotations.NotNull
        java.util.List<com.classicsviewer.app.models.TextLine> lines, @org.jetbrains.annotations.NotNull
        java.lang.String language, boolean isGreek, @org.jetbrains.annotations.NotNull
        kotlin.jvm.functions.Function1<? super java.lang.String, kotlin.Unit> onWordClick, @org.jetbrains.annotations.Nullable
        java.util.List<com.classicsviewer.app.models.TranslationSegment> translationSegments, @org.jetbrains.annotations.Nullable
        java.lang.String translator) {
            return null;
        }
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0016\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\bf\u0018\u00002\u00020\u0001J\u0010\u0010\u0002\u001a\u00020\u00032\u0006\u0010\u0004\u001a\u00020\u0005H&\u00a8\u0006\u0006"}, d2 = {"Lcom/classicsviewer/app/fragments/TextPageFragment$OnWordClickListener;", "", "onWordClick", "", "word", "", "app_debug"})
    public static abstract interface OnWordClickListener {
        
        public abstract void onWordClick(@org.jetbrains.annotations.NotNull
        java.lang.String word);
    }
}