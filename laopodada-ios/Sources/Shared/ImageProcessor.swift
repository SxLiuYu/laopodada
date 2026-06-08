import UIKit

/// Compresses and resizes an image to a sane upload size.
/// - Returns: JPEG data ≤ ~1MB at longest edge 2048px.
enum ImageProcessor {
    static func prepareForUpload(_ image: UIImage, maxEdge: CGFloat = 2048, quality: CGFloat = 0.8) -> Data? {
        let resized = resize(image, maxEdge: maxEdge)
        return resized.jpegData(compressionQuality: quality)
    }

    private static func resize(_ image: UIImage, maxEdge: CGFloat) -> UIImage {
        let size = image.size
        let longest = max(size.width, size.height)
        guard longest > maxEdge else { return image }
        let scale = maxEdge / longest
        let newSize = CGSize(width: size.width * scale, height: size.height * scale)
        let renderer = UIGraphicsImageRenderer(size: newSize)
        return renderer.image { _ in
            image.draw(in: CGRect(origin: .zero, size: newSize))
        }
    }
}
