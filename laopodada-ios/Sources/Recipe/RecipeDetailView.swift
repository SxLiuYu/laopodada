import SwiftUI

struct RecipeDetailView: View {
    let recipe: Recipe
    var onDeleted: () -> Void

    @EnvironmentObject private var appState: AppState
    @State private var showDeleteConfirm = false
    @State private var isDeleting = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                cover

                // Title + meta
                VStack(alignment: .leading, spacing: 8) {
                    Text(recipe.title)
                        .font(.title2)
                        .fontWeight(.bold)
                    HStack(spacing: 10) {
                        metaChip(recipe.categoryDisplay, system: "tag")
                        metaChip(recipe.difficultyDisplay + " " + RecipeDifficulty(rawValue: recipe.difficulty)?.emoji ?? "",
                                 system: "speedometer")
                        if let mins = recipe.totalMinutes {
                            metaChip("\(mins) 分钟", system: "clock")
                        }
                        if let s = recipe.servings {
                            metaChip("\(s) 人份", system: "person.2")
                        }
                    }
                }
                .padding(.horizontal)

                if !recipe.tags.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            ForEach(recipe.tags, id: \.self) { tag in
                                Text("#\(tag)")
                                    .font(.caption)
                                    .padding(.horizontal, 8).padding(.vertical, 4)
                                    .background(Color(.tertiarySystemFill))
                                    .clipShape(Capsule())
                            }
                        }
                        .padding(.horizontal)
                    }
                }

                ingredients
                steps

                if let note = recipe.note, !note.isEmpty {
                    noteSection(note)
                }
            }
            .padding(.vertical)
        }
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(role: .destructive) {
                    showDeleteConfirm = true
                } label: {
                    Image(systemName: "trash")
                }
            }
        }
        .confirmationDialog("删除这个食谱?", isPresented: $showDeleteConfirm) {
            Button("删除", role: .destructive) { Task { await delete() } }
            Button("取消", role: .cancel) {}
        } message: {
            Text("「\(recipe.title)」将被永久删除")
        }
    }

    @ViewBuilder
    private var cover: some View {
        if let url = recipe.coverURL {
            AsyncImage(url: url) { phase in
                switch phase {
                case .success(let img): img.resizable().scaledToFill()
                case .failure: Color(.tertiarySystemFill)
                case .empty: ProgressView()
                @unknown default: Color(.tertiarySystemFill)
                }
            }
            .frame(height: 220)
            .clipped()
        }
    }

    private func metaChip(_ text: String, system: String) -> some View {
        HStack(spacing: 4) {
            Image(systemName: system).font(.caption2)
            Text(text).font(.caption)
        }
        .padding(.horizontal, 8).padding(.vertical, 4)
        .background(Color(.tertiarySystemFill))
        .clipShape(Capsule())
    }

    private var ingredients: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("食材", systemImage: "list.bullet.rectangle")
                .font(.headline)
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(recipe.ingredients.enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top) {
                        Text("·").foregroundStyle(.secondary)
                        Text(item)
                    }
                    .font(.subheadline)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .padding(.horizontal)
    }

    private var steps: some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("步骤", systemImage: "list.number")
                .font(.headline)
            VStack(alignment: .leading, spacing: 12) {
                ForEach(Array(recipe.steps.enumerated()), id: \.offset) { idx, step in
                    HStack(alignment: .top, spacing: 10) {
                        Text("\(idx + 1)")
                            .font(.caption)
                            .fontWeight(.bold)
                            .frame(width: 22, height: 22)
                            .background(Color.accentColor)
                            .foregroundStyle(.white)
                            .clipShape(Circle())
                        Text(step)
                            .font(.subheadline)
                    }
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .padding(.horizontal)
    }

    private func noteSection(_ note: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("小贴士", systemImage: "lightbulb")
                .font(.headline)
            Text(note)
                .font(.subheadline)
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .padding(.horizontal)
    }

    private func delete() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await RecipeAPI(client: appState.api).delete(recipe.id)
            onDeleted()
        } catch {
            // surface via navigation; kept minimal
            print("delete failed: \(error)")
        }
    }
}
