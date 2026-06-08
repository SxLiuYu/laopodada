import SwiftUI
import UIKit

struct WardrobeAddView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.dismiss) private var dismiss

    @State private var pickedImage: UIImage?
    @State private var showingCamera = false
    @State private var showingLibrary = false
    @State private var category: WardrobeCategory = .top
    @State private var title: String = ""
    @State private var brand: String = ""
    @State private var color: String = ""
    @State private var isUploading = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("图片") {
                    if let img = pickedImage {
                        Image(uiImage: img)
                            .resizable()
                            .scaledToFit()
                            .frame(maxHeight: 240)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        Button("重新选择", role: .destructive) { pickedImage = nil }
                    } else {
                        Button {
                            showingCamera = true
                        } label: {
                            Label("拍照", systemImage: "camera")
                        }
                        Button {
                            showingLibrary = true
                        } label: {
                            Label("从相册选择", systemImage: "photo.on.rectangle")
                        }
                    }
                }

                Section("信息") {
                    TextField("名称 (必填)", text: $title)
                    Picker("类别", selection: $category) {
                        ForEach(WardrobeCategory.allCases) { c in
                            Label(c.displayName, systemImage: c.systemImage).tag(c)
                        }
                    }
                    TextField("品牌 (选填)", text: $brand)
                    TextField("颜色 (选填)", text: $color)
                }

                if let msg = errorMessage {
                    Section { Text(msg).foregroundStyle(.red).font(.footnote) }
                }
            }
            .navigationTitle("添加衣物")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("上传") { Task { await upload() } }
                        .disabled(pickedImage == nil || title.isEmpty || isUploading)
                }
            }
            .sheet(isPresented: $showingCamera) {
                CameraPicker { img in
                    pickedImage = img
                    showingCamera = false
                }
                .ignoresSafeArea()
            }
            .sheet(isPresented: $showingLibrary) {
                PhotoPicker { img in
                    pickedImage = img
                    showingLibrary = false
                }
                .ignoresSafeArea()
            }
            .overlay {
                if isUploading {
                    ProgressView("上传中…")
                        .padding()
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private func upload() async {
        guard let img = pickedImage, let data = ImageProcessor.prepareForUpload(img) else {
            errorMessage = "图片处理失败"
            return
        }
        isUploading = true
        errorMessage = nil
        defer { isUploading = false }
        do {
            _ = try await WardrobeAPI(client: appState.api).upload(
                imageData: data,
                category: category,
                title: title,
                brand: brand.isEmpty ? nil : brand,
                color: color.isEmpty ? nil : color
            )
            dismiss()
        } catch {
            errorMessage = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
        }
    }
}
