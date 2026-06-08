import SwiftUI

struct RecipeAddView: View {
    var onCreated: (Recipe) -> Void

    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var title = ""
    @State private var category: RecipeCategory = .lunch
    @State private var difficulty: RecipeDifficulty = .easy
    @State private var prepMinutesText = ""
    @State private var cookMinutesText = ""
    @State private var servingsText = ""
    @State private var ingredientsText = ""   // newline-separated
    @State private var stepsText = ""         // newline-separated
    @State private var tagsText = ""          // comma-separated
    @State private var note = ""
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("基本信息") {
                    TextField("菜名", text: $title)
                        .textInputAutocapitalization(.never)
                    Picker("类别", selection: $category) {
                        ForEach(RecipeCategory.allCases) { Text($0.display).tag($0) }
                    }
                    Picker("难度", selection: $difficulty) {
                        ForEach(RecipeDifficulty.allCases) { Text($0.display).tag($0) }
                    }
                }

                Section("时间与份量") {
                    TextField("准备(分钟)", text: $prepMinutesText).keyboardType(.numberPad)
                    TextField("烹饪(分钟)", text: $cookMinutesText).keyboardType(.numberPad)
                    TextField("份数", text: $servingsText).keyboardType(.numberPad)
                }

                Section("食材 (每行一个)") {
                    TextEditor(text: $ingredientsText)
                        .frame(minHeight: 90)
                        .font(.body)
                }

                Section("步骤 (每行一步)") {
                    TextEditor(text: $stepsText)
                        .frame(minHeight: 140)
                        .font(.body)
                }

                Section("标签 (逗号分隔,可选)") {
                    TextField("如:快手菜,下饭,素", text: $tagsText)
                        .textInputAutocapitalization(.never)
                }

                Section("小贴士 (可选)") {
                    TextField("", text: $note, axis: .vertical)
                        .lineLimit(2...4)
                }
            }
            .navigationTitle("添加食谱")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("保存") { Task { await save() } }
                        .disabled(!canSave || isSaving)
                }
            }
            .alert("出错了", isPresented: .constant(errorMessage != nil), actions: {
                Button("好") { errorMessage = nil }
            }, message: { Text(errorMessage ?? "") })
            .overlay {
                if isSaving {
                    Color.black.opacity(0.2).ignoresSafeArea()
                    ProgressView("保存中…")
                        .padding()
                        .background(.regularMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private var canSave: Bool {
        !title.trimmingCharacters(in: .whitespaces).isEmpty &&
        !ingredientsText.trimmingCharacters(in: .whitespaces).isEmpty &&
        !stepsText.trimmingCharacters(in: .whitespaces).isEmpty
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let ingredients = ingredientsText
                .split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
            let steps = stepsText
                .split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
            let tags = tagsText
                .split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
            let prep = Int(prepMinutesText.trimmingCharacters(in: .whitespaces))
            let cook = Int(cookMinutesText.trimmingCharacters(in: .whitespaces))
            let serv = Int(servingsText.trimmingCharacters(in: .whitespaces))
            let noteVal = note.trimmingCharacters(in: .whitespaces)

            let recipe = try await RecipeAPI(client: appState.api).create(
                title: title.trimmingCharacters(in: .whitespaces),
                category: category.rawValue,
                difficulty: difficulty.rawValue,
                prepMinutes: prep,
                cookMinutes: cook,
                servings: serv,
                ingredients: ingredients,
                steps: steps,
                tags: tags,
                note: noteVal.isEmpty ? nil : noteVal
            )
            onCreated(recipe)
            dismiss()
        } catch {
            errorMessage = "保存失败: \(error.localizedDescription)"
        }
    }
}
