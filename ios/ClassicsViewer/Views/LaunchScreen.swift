import SwiftUI

struct LaunchScreen: View {
    @State private var isAnimating = false
    
    var body: some View {
        VStack(spacing: 30) {
            Image(systemName: "book.fill")
                .font(.system(size: 80))
                .foregroundColor(.blue)
                .scaleEffect(isAnimating ? 1.1 : 1.0)
                .animation(.easeInOut(duration: 1.5).repeatForever(autoreverses: true), value: isAnimating)
            
            Text("Classics Viewer")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            ProgressView("Initializing database...")
                .progressViewStyle(CircularProgressViewStyle())
                .scaleEffect(1.2)
        }
        .onAppear {
            isAnimating = true
        }
    }
}
