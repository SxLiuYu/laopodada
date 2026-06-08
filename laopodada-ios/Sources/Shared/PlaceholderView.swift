import SwiftUI

/// Generic "coming soon" placeholder for modules not yet built.
struct PlaceholderView: View {
    let title: String
    let systemImage: String
    let message: String

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: systemImage)
                .font(.system(size: 64))
                .foregroundStyle(.tertiary)
            Text(title)
                .font(.title.bold())
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(uiColor: .systemGroupedBackground))
    }
}

#Preview {
    PlaceholderView(title: "食谱", systemImage: "fork.knife", message: "下一阶段")
}
