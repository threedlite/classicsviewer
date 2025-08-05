package com.classicsviewer.app;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000:\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000b\n\u0000\n\u0002\u0018\u0002\n\u0002\u0010\u0002\n\u0002\b\u0002\n\u0002\u0010\b\n\u0002\b\u0005\n\u0002\u0018\u0002\n\u0002\b\u0003\u0018\u00002\b\u0012\u0004\u0012\u00020\u00020\u0001:\u0001\u0015B1\u0012\f\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004\u0012\b\b\u0002\u0010\u0006\u001a\u00020\u0007\u0012\u0012\u0010\b\u001a\u000e\u0012\u0004\u0012\u00020\u0005\u0012\u0004\u0012\u00020\n0\t\u00a2\u0006\u0002\u0010\u000bJ\b\u0010\f\u001a\u00020\rH\u0016J\u0018\u0010\u000e\u001a\u00020\n2\u0006\u0010\u000f\u001a\u00020\u00022\u0006\u0010\u0010\u001a\u00020\rH\u0016J\u0018\u0010\u0011\u001a\u00020\u00022\u0006\u0010\u0012\u001a\u00020\u00132\u0006\u0010\u0014\u001a\u00020\rH\u0016R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u001a\u0010\b\u001a\u000e\u0012\u0004\u0012\u00020\u0005\u0012\u0004\u0012\u00020\n0\tX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0014\u0010\u0003\u001a\b\u0012\u0004\u0012\u00020\u00050\u0004X\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0016"}, d2 = {"Lcom/classicsviewer/app/WorkAdapter;", "Landroidx/recyclerview/widget/RecyclerView$Adapter;", "Lcom/classicsviewer/app/WorkAdapter$ViewHolder;", "works", "", "Lcom/classicsviewer/app/models/Work;", "invertColors", "", "onWorkClick", "Lkotlin/Function1;", "", "(Ljava/util/List;ZLkotlin/jvm/functions/Function1;)V", "getItemCount", "", "onBindViewHolder", "holder", "position", "onCreateViewHolder", "parent", "Landroid/view/ViewGroup;", "viewType", "ViewHolder", "app_debug"})
public final class WorkAdapter extends androidx.recyclerview.widget.RecyclerView.Adapter<com.classicsviewer.app.WorkAdapter.ViewHolder> {
    @org.jetbrains.annotations.NotNull
    private final java.util.List<com.classicsviewer.app.models.Work> works = null;
    private final boolean invertColors = false;
    @org.jetbrains.annotations.NotNull
    private final kotlin.jvm.functions.Function1<com.classicsviewer.app.models.Work, kotlin.Unit> onWorkClick = null;
    
    public WorkAdapter(@org.jetbrains.annotations.NotNull
    java.util.List<com.classicsviewer.app.models.Work> works, boolean invertColors, @org.jetbrains.annotations.NotNull
    kotlin.jvm.functions.Function1<? super com.classicsviewer.app.models.Work, kotlin.Unit> onWorkClick) {
        super();
    }
    
    @java.lang.Override
    @org.jetbrains.annotations.NotNull
    public com.classicsviewer.app.WorkAdapter.ViewHolder onCreateViewHolder(@org.jetbrains.annotations.NotNull
    android.view.ViewGroup parent, int viewType) {
        return null;
    }
    
    @java.lang.Override
    public void onBindViewHolder(@org.jetbrains.annotations.NotNull
    com.classicsviewer.app.WorkAdapter.ViewHolder holder, int position) {
    }
    
    @java.lang.Override
    public int getItemCount() {
        return 0;
    }
    
    @kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000\u0012\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004R\u0011\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\b\n\u0000\u001a\u0004\b\u0005\u0010\u0006\u00a8\u0006\u0007"}, d2 = {"Lcom/classicsviewer/app/WorkAdapter$ViewHolder;", "Landroidx/recyclerview/widget/RecyclerView$ViewHolder;", "binding", "Lcom/classicsviewer/app/databinding/ItemTextBinding;", "(Lcom/classicsviewer/app/databinding/ItemTextBinding;)V", "getBinding", "()Lcom/classicsviewer/app/databinding/ItemTextBinding;", "app_debug"})
    public static final class ViewHolder extends androidx.recyclerview.widget.RecyclerView.ViewHolder {
        @org.jetbrains.annotations.NotNull
        private final com.classicsviewer.app.databinding.ItemTextBinding binding = null;
        
        public ViewHolder(@org.jetbrains.annotations.NotNull
        com.classicsviewer.app.databinding.ItemTextBinding binding) {
            super(null);
        }
        
        @org.jetbrains.annotations.NotNull
        public final com.classicsviewer.app.databinding.ItemTextBinding getBinding() {
            return null;
        }
    }
}