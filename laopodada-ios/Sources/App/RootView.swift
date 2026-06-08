import SwiftUI

/// Root tab view. 老婆哒哒 v0.1 ships 衣橱 (Wardrobe) fully; 食谱 and 健康知识 are placeholders.
struct RootView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selection: Tab = .wardrobe

    enum Tab: Hashable { case wardrobe, recipe, health }

    var body: some View {
        TabView(selection: $selection) {
            NavigationStack {
                WardrobeListView()
            }
            .tabItem { Label("衣橱", systemImage: "tshirt.fill") }
            .tag(Tab.wardrobe)

            NavigationStack {
                PlaceholderView(title: "食谱", systemImage: "fork.knife", message: "下一阶段")
            }
            .tabItem { Label("食谱", systemImage: "fork.knife") }
            .tag(Tab.recipe)

            NavigationStack {
                PlaceholderView(title: "健康知识", systemImage: "heart.text.square.fill", message: "下一阶段")
            }
            .tabItem { Label("健康", systemImage: "heart.text.square.fill") }
            .tag(Tab.health)
        }
        .tint(.pink)
    }
}
