import SwiftUI

struct WardrobeDetailView: View {
    let item: WardrobeItem
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var isDeleting = false
    @State private var deleteError: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                AsyncImage(url: item.originalURL) { phase in
                    switch phase {
                    case .empty: ProgressView().frame(maxWidth: .infinity, minHeight: 320)
                    case .success(let img):
                        img.resizable().scaledToFit()
                            .frame(maxWidth: .infinity)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                    case .failure:
                        Image(systemName: "photo").font(.system(size: 64)).foregroundStyle(.secondary)
                    @unknown default: EmptyView()
                    }
                }

                Group {
                    LabeledContent("名称", value: item.title)
                    LabeledContent("类别", value: categoryDisplayName(item.category))
                    if let brand = item.brand, !brand.isEmpty {
                        LabeledContent("品牌", value: brand)
                    }
                    if let color = item.color, !color.isEmpty {
                        LabeledContent("颜色", value: color)
                    }
                    LabeledContent("添加时间") {
                        Text(item.createdAt, style: .date)
                    }
                }
                .font(.body)
            }
            .padding()
        }
        .navigationTitle(item.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(role: .destructive) {
                    Task { await deleteItem() }
                } label: {
                    if isDeleting { ProgressView() } else { Image(systemName: "trash") }
                }
                .disabled(isDeleting)
            }
        }
        .alert("删除失败", isPresented: .constant(deleteError != nil), actions: {
            Button("好") { deleteError = nil }
        }, message: {
            Text(deleteError ?? "")
        })
    }

    private func deleteItem() async {
        isDeleting = true
        defer { isDeleting = false }
        do {
            try await WardrobeAPI(client: appState.api).delete(id: item.id)
            dismiss()
        } catch {
            deleteError = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }

    private func categoryDisplayName(_ raw: String) -> String {
        WardrobeCategory(rawValue: raw)?.displayName ?? raw
    }
}
