package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u000e\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0005\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\b\u0012\u0004\u0012\u00020\u00020\u0001:\u0002\u0016\u0017B1\u0012\f\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004\u0012\u0012\u0010\u0006\u001a\u000e\u0012\u0004\u0012\u00020\b\u0012\u0004\u0012\u00020\t0\u0007\u0012\b\b\u0002\u0010\n\u001a\u00020\u000b\u00a2\u0006\u0002\u0010\fJ\b\u0010\r\u001a\u00020\u000eH\u0016J\u0018\u0010\u000f\u001a\u00020\t2\u0006\u0010\u0010\u001a\u00020\u00022\u0006\u0010\u0011\u001a\u00020\u000eH\u0016J\u0018\u0010\u0012\u001a\u00020\u00022\u0006\u0010\u0013\u001a\u00020\u00142\u0006\u0010\u0015\u001a\u00020\u000eH\u0016R\u000e\u0010\n\u001a\u00020\u000bX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u001a\u0010\u0006\u001a\u000e\u0012\u0004\u0012\u00020\b\u0012\u0004\u0012\u00020\t0\u0007X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0018"}, d2 = {"Lcom/classicsviewer/app/TextLineAdapter;", "Landroidx/recyclerview/widget/RecyclerView$Adapter;", "Lcom/classicsviewer/app/TextLineAdapter$ViewHolder;", "lines", "", "Lcom/classicsviewer/app/models/TextLine;", "onWordClick", "Lkotlin/Function1;", "", "", "invertColors", "", "(Ljava/util/List;Lkotlin/jvm/functions/Function1;Z)V", "getItemCount", "", "onBindViewHolder", "holder", "position", "onCreateViewHolder", "parent", "Landroid/view/ViewGroup;", "viewType", "NoUnderlineClickableSpan", "ViewHolder", "app_debug"})
public final class TextLineAdapter extends androidx.recyclerview.widget.RecyclerView.Adapter<com.classicsviewer.app.TextLineAdapter.ViewHolder> {
    @org.jetbrains.annotations.NotNull
    private final java.util.List<com.classicsviewer.app.models.TextLine> lines = null;
    @org.jetbrains.annotations.NotNull
    private final kotlin.jvm.functions.Function1<java.lang.String, kotlin.Unit> onWordClick = null;
    private final boolean invertColors = false;
    
    public TextLineAdapter(@org.jetbrains.annotations.NotNull
    java.util.List<com.classicsviewer.app.models.TextLine> lines, @org.jetbrains.annotations.NotNull
    kotlin.jvm.functions.Function1<? super java.lang.String, kotlin.Unit> onWordClick, boolean invertColors) {
        super();
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.NotNull
    public com.classicsviewer.app.TextLineAdapter.ViewHolder onCreateViewHolder(@org.jetbrains.annotations.NotNull
    android.view.ViewGroup parent, int viewType) {
        return null;
    }
    
    @java.lang.Override
    public void onBindViewHolder(@org.jetbrains.annotations.NotNull
    com.classicsviewer.app.TextLineAdapter.ViewHolder holder, int position) {
    }
    
    @java.lang.Override
    public int getItemCount() {
        return 0;
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000$\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u0002\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\b\u0082\u0004\u0018\u00002\u00020\u0001B\u0013\u0012\f\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u0003\u00a2\u0006\u0002\u0010\u0005J\u0010\u0010\u0006\u001a\u00020\u00042\u0006\u0010\u0007\u001a\u00020\bH\u0016J\u0010\u0010\t\u001a\u00020\u00042\u0006\u0010\n\u001a\u00020\u000bH\u0016R\u0014\u0010\u0002\u001a\b\u0012\u0004\u0012\u00020\u00040\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\f"}, d2 = {"Lcom/classicsviewer/app/TextLineAdapter$NoUnderlineClickableSpan;", "Landroid/text/style/ClickableSpan;", "clickAction", "Lkotlin/Function0;", "", "(Lcom/classicsviewer/app/TextLineAdapter;Lkotlin/jvm/functions/Function0;)V", "onClick", "widget", "Landroid/view/View;", "updateDrawState", "ds", "Landroid/text/TextPaint;", "app_debug"})
    final class NoUnderlineClickableSpan extends android.text.style.ClickableSpan {
        @org.jetbrains.annotations.NotNull
        private final kotlin.jvm.functions.Function0<kotlin.Unit> clickAction = null;
        
        public NoUnderlineClickableSpan(@org.jetbrains.annotations.NotNull
        kotlin.jvm.functions.Function0<kotlin.Unit> clickAction) {
            super();
        }
        
        @java.lang.Override
        public void onClick(@org.jetbrains.annotations.NotNull
        android.view.View widget) {
        }
        
        @java.lang.Override
        public void updateDrawState(@org.jetbrains.annotations.NotNull
        android.text.TextPaint ds) {
        }
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0012\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004R\u0011\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0005\u0010\u0006\u00a8\u0006\u0007"}, d2 = {"Lcom/classicsviewer/app/TextLineAdapter$ViewHolder;", "Landroidx/recyclerview/widget/RecyclerView$ViewHolder;", "binding", "Lcom/classicsviewer/app/databinding/ItemTextLineBinding;", "(Lcom/classicsviewer/app/databinding/ItemTextLineBinding;)V", "getBinding", "()Lcom/classicsviewer/app/databinding/ItemTextLineBinding;", "app_debug"})
    public static final class ViewHolder extends androidx.recyclerview.widget.RecyclerView.ViewHolder {
        @org.jetbrains.annotations.NotNull
        private final com.classicsviewer.app.databinding.ItemTextLineBinding binding = null;
        
        public ViewHolder(@org.jetbrains.annotations.NotNull
        com.classicsviewer.app.databinding.ItemTextLineBinding binding) {
            super(null);
        }
        
        @org.jetbrains.annotations.NotNull
        public final com.classicsviewer.app.databinding.ItemTextLineBinding getBinding() {
            return null;
        }
    }
}