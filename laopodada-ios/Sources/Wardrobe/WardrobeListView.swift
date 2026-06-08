import SwiftUI

struct WardrobeListView: View {
    @EnvironmentObject private var appState: AppState
    @State private var items: [WardrobeItem] = []
    @State private var selectedCategory: WardrobeCategory? = nil
    @State private var isLoading: Bool = false
    @State private var errorMessage: String?
    @State private var showingAdd = false

    private var api: WardrobeAPI { WardrobeAPI(client: appState.api) }

    private let columns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12),
    ]

    var body: some View {
        Group {
            if isLoading && items.isEmpty {
                ProgressView().controlSize(.large)
            } else if let msg = errorMessage, items.isEmpty {
                ContentUnavailableView {
                    Label("加载失败", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(msg)
                } actions: {
                    Button("重试") { Task { await load() } }
                        .buttonStyle(.borderedProminent)
                }
            } else if items.isEmpty {
                ContentUnavailableView {
                    Label("衣橱是空的", systemImage: "tshirt")
                } description: {
                    Text("点击右上角 ＋ 开始添加第一件衣物")
                } actions: {
                    Button("添加") { showingAdd = true }
                        .buttonStyle(.borderedProminent)
                }
            } else {
                ScrollView {
                    LazyVGrid(columns: columns, spacing: 12) {
                        ForEach(items) { item in
                            NavigationLink(value: item) {
                                WardrobeThumbnail(item: item)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.top, 4)
                }
                .refreshable { await load() }
            }
        }
        .navigationTitle("衣橱")
        .navigationDestination(for: WardrobeItem.self) { item in
            WardrobeDetailView(item: item)
        }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Menu {
                    Button("全部") { Task { await setCategory(nil) } }
                    Divider()
                    ForEach(WardrobeCategory.allCases) { c in
                        Button {
                            Task { await setCategory(c) }
                        } label: {
                            Label(c.displayName, systemImage: c.systemImage)
                        }
                    }
                } label: {
                    Image(systemName: selectedCategory?.systemImage ?? "line.3.horizontal.decrease.circle")
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button { showingAdd = true } label: {
                    Image(systemName: "plus.circle.fill")
                        .font(.title3)
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            WardrobeAddView()
        }
        .task { await load() }
        .onChange(of: showingAdd) { _, isShowing in
            // Refresh when the add sheet closes (a new item may have been uploaded).
            if !isShowing { Task { await load() } }
        }
    }

    private func load() async {
        isLoading = true
        errorMessage = nil
        do {
            items = try await api.list(category: selectedCategory)
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
        isLoading = false
    }

    private func setCategory(_ category: WardrobeCategory?) async {
        selectedCategory = category
        await load()
    }
}

private struct WardrobeThumbnail: View {
    let item: WardrobeItem

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            AsyncImage(url: item.thumbnailURL) { phase in
                switch phase {
                case .empty:
                    RoundedRectangle(cornerRadius: 8).fill(.gray.opacity(0.15))
                        .overlay(ProgressView())
                case .success(let img):
                    img.resizable().scaledToFill()
                case .failure:
                    RoundedRectangle(cornerRadius: 8).fill(.gray.opacity(0.15))
                        .overlay(Image(systemName: "photo").foregroundStyle(.secondary))
                @unknown default:
                    EmptyView()
                }
            }
            .frame(maxWidth: .infinity)
            .aspectRatio(1, contentMode: .fit)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Text(item.title)
                .font(.caption)
                .lineLimit(1)
            if let brand = item.brand, !brand.isEmpty {
                Text(brand)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
        }
    }
}
