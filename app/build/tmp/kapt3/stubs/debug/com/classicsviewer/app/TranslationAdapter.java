package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u00006\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000b\n\u0002\b\u0002\n\u0002\u0010\b\n\u0000\n\u0002\u0010\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0003\u0018\u00002\b\u0012\u0004\u0012\u00020\u00020\u0001:\u0001\u0013B\u001d\u0012\f\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004\u0012\b\b\u0002\u0010\u0006\u001a\u00020\u0007\u00a2\u0006\u0002\u0010\bJ\b\u0010\t\u001a\u00020\nH\u0016J\u0018\u0010\u000b\u001a\u00020\f2\u0006\u0010\r\u001a\u00020\u00022\u0006\u0010\u000e\u001a\u00020\nH\u0016J\u0018\u0010\u000f\u001a\u00020\u00022\u0006\u0010\u0010\u001a\u00020\u00112\u0006\u0010\u0012\u001a\u00020\nH\u0016R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0014"}, d2 = {"Lcom/classicsviewer/app/TranslationAdapter;", "Landroidx/recyclerview/widget/RecyclerView$Adapter;", "Lcom/classicsviewer/app/TranslationAdapter$ViewHolder;", "segments", "", "Lcom/classicsviewer/app/fragments/TranslationDisplayItem;", "invertColors", "", "(Ljava/util/List;Z)V", "getItemCount", "", "onBindViewHolder", "", "holder", "position", "onCreateViewHolder", "parent", "Landroid/view/ViewGroup;", "viewType", "ViewHolder", "app_debug"})
public final class TranslationAdapter extends androidx.recyclerview.widget.RecyclerView.Adapter<com.classicsviewer.app.TranslationAdapter.ViewHolder> {
    @org.jetbrains.annotations.NotNull
    private final java.util.List<com.classicsviewer.app.fragments.TranslationDisplayItem> segments = null;
    private final boolean invertColors = false;
    
    public TranslationAdapter(@org.jetbrains.annotations.NotNull
    java.util.List<com.classicsviewer.app.fragments.TranslationDisplayItem> segments, boolean invertColors) {
        super();
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.NotNull
    public com.classicsviewer.app.TranslationAdapter.ViewHolder onCreateViewHolder(@org.jetbrains.annotations.NotNull
    android.view.ViewGroup parent, int viewType) {
        return null;
    }
    
    @java.lang.Override
    public void onBindViewHolder(@org.jetbrains.annotations.NotNull
    com.classicsviewer.app.TranslationAdapter.ViewHolder holder, int position) {
    }
    
    @java.lang.Override
    public int getItemCount() {
        return 0;
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0012\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004R\u0011\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0005\u0010\u0006\u00a8\u0006\u0007"}, d2 = {"Lcom/classicsviewer/app/TranslationAdapter$ViewHolder;", "Landroidx/recyclerview/widget/RecyclerView$ViewHolder;", "binding", "Lcom/classicsviewer/app/databinding/ItemTranslationSegmentBinding;", "(Lcom/classicsviewer/app/databinding/ItemTranslationSegmentBinding;)V", "getBinding", "()Lcom/classicsviewer/app/databinding/ItemTranslationSegmentBinding;", "app_debug"})
    public static final class ViewHolder extends androidx.recyclerview.widget.RecyclerView.ViewHolder {
        @org.jetbrains.annotations.NotNull
        private final com.classicsviewer.app.databinding.ItemTranslationSegmentBinding binding = null;
        
        public ViewHolder(@org.jetbrains.annotations.NotNull
        com.classicsviewer.app.databinding.ItemTranslationSegmentBinding binding) {
            super(null);
        }
        
        @org.jetbrains.annotations.NotNull
        public final com.classicsviewer.app.databinding.ItemTranslationSegmentBinding getBinding() {
            return null;
        }
    }
}