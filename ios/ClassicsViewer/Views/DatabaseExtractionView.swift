import SwiftUI

struct DatabaseExtractionView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        VStack(spacing: 30) {
            Spacer()
            
            Image(systemName: "doc.zipper")
                .font(.system(size: 80))
                .foregroundColor(.blue)
            
            Text("Extracting Database")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("Please wait while we prepare the classical texts for first use.")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            ProgressView(value: appState.extractionProgress)
                .progressViewStyle(LinearProgressViewStyle())
                .padding(.horizontal, 50)
            
            Text("\(Int(appState.extractionProgress * 100))%")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Spacer()
            
            Text("This is a one-time process")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
    }
}

struct DatabaseExtractionView_Previews: PreviewProvider {
    static var previews: some View {
        let appState = AppState()
        appState.isExtracting = true
        appState.extractionProgress = 0.45
        
        return DatabaseExtractionView()
            .environmentObject(appState)
    }
}