import SwiftUI

struct RecipeListView: View {
    @EnvironmentObject private var appState: AppState
    @State private var recipes: [Recipe] = []
    @State private var selectedCategory: String? = nil
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showingAdd = false

    var body: some View {
        NavigationStack {
            ZStack {
                if recipes.isEmpty && isLoading {
                    ProgressView("加载中…")
                } else if recipes.isEmpty {
                    emptyState
                } else {
                    listContent
                }
            }
            .navigationTitle("食谱")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showingAdd = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.title2)
                    }
                }
            }
            .refreshable { await load() }
            .task { await load() }
            .sheet(isPresented: $showingAdd) {
                RecipeAddView(onCreated: { _ in
                    Task { await load() }
                })
            }
            .alert("出错了", isPresented: .constant(errorMessage != nil), actions: {
                Button("好") { errorMessage = nil }
            }, message: { Text(errorMessage ?? "") })
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "fork.knife.circle")
                .font(.system(size: 64))
                .foregroundStyle(.tertiary)
            Text("还没有食谱")
                .font(.title3)
                .foregroundStyle(.secondary)
            Button("添加第一个食谱") { showingAdd = true }
                .buttonStyle(.borderedProminent)
        }
    }

    private var listContent: some View {
        VStack(spacing: 0) {
            // Category filter chips
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    chip(label: "全部", value: nil)
                    ForEach(RecipeCategory.allCases) { cat in
                        chip(label: cat.display, value: cat.rawValue)
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
            }
            .background(Color(.systemGroupedBackground))

            List {
                ForEach(recipes) { recipe in
                    NavigationLink {
                        RecipeDetailView(recipe: recipe, onDeleted: {
                            Task { await load() }
                        })
                    } label: {
                        RecipeRowView(recipe: recipe)
                    }
                }
            }
            .listStyle(.plain)
        }
    }

    private func chip(label: String, value: String?) -> some View {
        let isSelected = selectedCategory == value
        return Button {
            selectedCategory = value
            Task { await load() }
        } label: {
            Text(label)
                .font(.subheadline)
                .fontWeight(isSelected ? .semibold : .regular)
                .padding(.horizontal, 14)
                .padding(.vertical, 6)
                .background(isSelected ? Color.accentColor : Color(.tertiarySystemFill))
                .foregroundStyle(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let api = RecipeAPI(client: appState.api)
            recipes = try await api.list(category: selectedCategory)
        } catch {
            errorMessage = "加载失败: \(error.localizedDescription)"
        }
    }
}

struct RecipeRowView: View {
    let recipe: Recipe

    var body: some View {
        HStack(spacing: 12) {
            // Cover
            if let url = recipe.coverURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let img): img.resizable().scaledToFill()
                    case .failure: Image(systemName: "photo").foregroundStyle(.tertiary)
                    case .empty: ProgressView()
                    @unknown default: EmptyView()
                    }
                }
                .frame(width: 64, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.tertiarySystemFill))
                    .frame(width: 64, height: 64)
                    .overlay {
                        Text(recipe.categoryDisplay.prefix(1))
                            .font(.title2)
                            .foregroundStyle(.secondary)
                    }
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(recipe.title)
                    .font(.headline)
                    .lineLimit(1)
                HStack(spacing: 6) {
                    Text(recipe.categoryDisplay)
                        .font(.caption)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.15))
                        .clipShape(Capsule())
                    Text(recipe.difficultyDisplay)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if let mins = recipe.totalMinutes {
                        Text("· \(mins) 分钟")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                if !recipe.tags.isEmpty {
                    Text(recipe.tags.prefix(3).joined(separator: " · "))
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 4)
    }
}
