import SwiftUI

struct AuthorListView: View {
    @EnvironmentObject var appState: AppState
    @StateObject private var viewModel: AuthorListViewModel
    @State private var showOnlyTranslated = false
    @State private var searchText = ""

    init() {
        // This will be overridden by onAppear with the actual language
        _viewModel = StateObject(wrappedValue: AuthorListViewModel(language: "greek"))
    }
    
    var body: some View {
        VStack {
            if viewModel.isLoading {
                LoadingView(message: "Loading authors...")
            } else if let error = viewModel.errorMessage {
                ErrorView(message: error) {
                    viewModel.loadAuthors()
                }
            } else {
                VStack(spacing: 0) {
                    searchBar
                    authorList
                }
            }
        }
        .navigationTitle("\(appState.selectedLanguage?.displayName ?? "") Authors")
        .navigationBarTitleDisplayMode(.large)
        .onAppear {
            // Update view model with correct language
            viewModel.language = appState.selectedLanguage?.id ?? "greek"
            viewModel.isGreek = viewModel.language == "greek"
            // Load authors if needed
            if viewModel.authors.isEmpty {
                viewModel.loadAuthors()
            }
        }
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Change Language") {
                    // Clear language selection to go back
                    appState.selectedLanguage = nil
                    UserDefaults.standard.removeObject(forKey: "selectedLanguage")
                }
            }
            
            ToolbarItem(placement: .navigationBarTrailing) {
                NavigationLink(destination: SettingsView()) {
                    Image(systemName: "gearshape")
                }
            }
        }
    }
    
    private var searchBar: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField("Search authors...", text: $searchText)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .onChange(of: searchText) { newValue in
                        viewModel.searchText = newValue
                    }
                if !searchText.isEmpty {
                    Button(action: {
                        searchText = ""
                        viewModel.searchText = ""
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 8)

            Toggle("Show only with translations", isOn: $showOnlyTranslated)
                .padding(.horizontal)
                .padding(.bottom, 8)
                .onChange(of: showOnlyTranslated) { newValue in
                    viewModel.showOnlyTranslated = newValue
                }

            if viewModel.filteredAuthors.count < viewModel.authors.count {
                Text("Showing \(viewModel.filteredAuthors.count) of \(viewModel.authors.count) authors")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .padding(.bottom, 4)
            }

            Divider()
        }
        .background(Color(UIColor.systemBackground))
    }

    private var authorList: some View {
        ScrollViewReader { proxy in
            List {
                ForEach(viewModel.authorsByFirstLetter(), id: \.0) { letter, authors in
                    Section(header: Text(letter)) {
                        ForEach(authors) { author in
                            NavigationLink {
                                WorksListView(author: author)
                            } label: {
                                AuthorRow(author: author)
                            }
                        }
                    }
                }
            }
            .listStyle(InsetGroupedListStyle())
            .overlay(alignment: .trailing) {
                // Alphabet index
                if viewModel.searchText.isEmpty {
                    VStack(spacing: 0) {
                        ForEach(viewModel.authorsByFirstLetter().map { $0.0 }, id: \.self) { letter in
                            Text(letter)
                                .font(.caption2)
                                .foregroundColor(.blue)
                                .onTapGesture {
                                    withAnimation {
                                        proxy.scrollTo(letter, anchor: .top)
                                    }
                                }
                        }
                    }
                    .padding(.trailing, 5)
                }
            }
        }
    }
}

struct AuthorRow: View {
    let author: Author
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(author.name)
                .font(.headline)
                .fontWeight(author.hasTranslations == 1 ? .bold : .regular)
            
            if let nameAlt = author.nameAlt {
                Text(nameAlt)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

struct AuthorListView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            AuthorListView()
                .environmentObject(AppState())
        }
    }
}