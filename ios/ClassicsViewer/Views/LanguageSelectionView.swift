import SwiftUI

struct LanguageSelectionView: View {
    @EnvironmentObject var appState: AppState
    
    // Android Material Design colors
    let greekColor = Color(red: 0.298, green: 0.686, blue: 0.314) // #4CAF50 Material Green 500
    let latinColor = Color(red: 0.957, green: 0.263, blue: 0.212) // #F44336 Material Red 500
    
    var body: some View {
        VStack(spacing: 30) {
            Spacer()
            
            Text("Select Language")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Spacer()
            
            VStack(spacing: 20) {
                // Greek button
                Button(action: {
                    appState.selectLanguage(.greek)
                }) {
                    Text("Greek")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 30)
                        .background(greekColor)
                        .cornerRadius(8)
                }
                
                // Latin button
                Button(action: {
                    appState.selectLanguage(.latin)
                }) {
                    Text("Latin")
                        .font(.title2)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 30)
                        .background(latinColor)
                        .cornerRadius(8)
                }
            }
            .padding(.horizontal, 40)
            
            Spacer()
            Spacer()
        }
    }
}

struct LanguageSelectionView_Previews: PreviewProvider {
    static var previews: some View {
        LanguageSelectionView()
            .environmentObject(AppState())
    }
}