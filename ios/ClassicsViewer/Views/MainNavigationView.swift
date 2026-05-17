import SwiftUI

struct MainNavigationView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        TabView {
            NavigationStack {
                AuthorListView()
            }
            .tabItem {
                Label("Library", systemImage: "books.vertical")
            }
            
            NavigationStack {
                BookmarksView()
            }
            .tabItem {
                Label("Bookmarks", systemImage: "bookmark")
            }

            NavigationStack {
                RhetoricSectionListView()
            }
            .tabItem {
                Label("Rhetoric", systemImage: "text.book.closed")
            }
        }
    }
}

struct MainNavigationView_Previews: PreviewProvider {
    static var previews: some View {
        let appState = AppState()
        appState.selectedLanguage = .greek
        
        return MainNavigationView()
            .environmentObject(appState)
    }
}