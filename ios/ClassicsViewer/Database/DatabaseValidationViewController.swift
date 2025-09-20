import SwiftUI

/// A view controller for testing database schema validation
struct DatabaseValidationView: View {
    @State private var validationStatus: String = "Not started"
    @State private var isValidating: Bool = false
    @State private var errors: [String] = []
    @State private var warnings: [String] = []
    @State private var showDetails: Bool = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Status Section
                VStack(spacing: 10) {
                    HStack {
                        Text("Validation Status:")
                            .font(.headline)
                        Text(validationStatus)
                            .foregroundColor(statusColor)
                            .font(.system(.body, design: .monospaced))
                    }
                    
                    if isValidating {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle())
                    }
                }
                .padding()
                .background(Color.gray.opacity(0.1))
                .cornerRadius(10)
                
                // Validate Button
                Button(action: runValidation) {
                    Label("Run Schema Validation", systemImage: "checkmark.shield")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .disabled(isValidating)
                
                // Results Section
                if !errors.isEmpty || !warnings.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        // Errors
                        if !errors.isEmpty {
                            VStack(alignment: .leading, spacing: 5) {
                                Label("\(errors.count) Errors", systemImage: "xmark.circle.fill")
                                    .font(.headline)
                                    .foregroundColor(.red)
                                
                                if showDetails {
                                    ScrollView {
                                        VStack(alignment: .leading, spacing: 3) {
                                            ForEach(errors, id: \.self) { error in
                                                Text("• \(error)")
                                                    .font(.caption)
                                                    .foregroundColor(.red)
                                                    .padding(.leading)
                                            }
                                        }
                                    }
                                    .frame(maxHeight: 200)
                                }
                            }
                        }
                        
                        Divider()
                        
                        // Warnings
                        if !warnings.isEmpty {
                            VStack(alignment: .leading, spacing: 5) {
                                Label("\(warnings.count) Warnings", systemImage: "exclamationmark.triangle.fill")
                                    .font(.headline)
                                    .foregroundColor(.orange)
                                
                                if showDetails {
                                    ScrollView {
                                        VStack(alignment: .leading, spacing: 3) {
                                            ForEach(warnings, id: \.self) { warning in
                                                Text("• \(warning)")
                                                    .font(.caption)
                                                    .foregroundColor(.orange)
                                                    .padding(.leading)
                                            }
                                        }
                                    }
                                    .frame(maxHeight: 200)
                                }
                            }
                        }
                        
                        // Toggle Details Button
                        Button(action: { showDetails.toggle() }) {
                            Label(showDetails ? "Hide Details" : "Show Details", 
                                  systemImage: showDetails ? "chevron.up" : "chevron.down")
                                .font(.caption)
                        }
                    }
                    .padding()
                    .background(Color.gray.opacity(0.05))
                    .cornerRadius(10)
                }
                
                Spacer()
                
                // Info Section
                VStack(alignment: .leading, spacing: 5) {
                    Text("Schema Validation")
                        .font(.headline)
                    Text("This tool validates that the extracted database schema matches the bundled database schema exactly, including:")
                        .font(.caption)
                    Text("• Table structure and names")
                        .font(.caption)
                    Text("• Column names, types, and constraints")
                        .font(.caption)
                    Text("• Indexes and primary keys")
                        .font(.caption)
                    Text("• Foreign key relationships")
                        .font(.caption)
                }
                .padding()
                .background(Color.blue.opacity(0.05))
                .cornerRadius(10)
            }
            .padding()
            .navigationTitle("Database Schema Validator")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private var statusColor: Color {
        switch validationStatus {
        case "✅ Valid":
            return .green
        case "❌ Invalid":
            return .red
        case "⚠️ Valid with warnings":
            return .orange
        case "Validating...":
            return .blue
        default:
            return .secondary
        }
    }
    
    private func runValidation() {
        isValidating = true
        validationStatus = "Validating..."
        errors = []
        warnings = []
        
        Task {
            do {
                let result = try await DatabaseSchemaValidator.shared.validateDatabaseSchema()
                
                await MainActor.run {
                    errors = result.errors
                    warnings = result.warnings
                    
                    if result.isValid {
                        if warnings.isEmpty {
                            validationStatus = "✅ Valid"
                        } else {
                            validationStatus = "⚠️ Valid with warnings"
                        }
                    } else {
                        validationStatus = "❌ Invalid"
                    }
                    
                    isValidating = false
                }
            } catch {
                await MainActor.run {
                    validationStatus = "❌ Error"
                    errors = ["Validation failed: \(error.localizedDescription)"]
                    isValidating = false
                }
            }
        }
    }
}

// MARK: - Debug Menu Integration

extension SettingsView {
    /// Add this to your Settings/Debug menu to access validation
    var databaseValidationLink: some View {
        NavigationLink(destination: DatabaseValidationView()) {
            HStack {
                Image(systemName: "checkmark.shield")
                    .foregroundColor(.blue)
                Text("Database Schema Validation")
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundColor(.gray)
            }
        }
    }
}

// MARK: - Preview

struct DatabaseValidationView_Previews: PreviewProvider {
    static var previews: some View {
        DatabaseValidationView()
    }
}