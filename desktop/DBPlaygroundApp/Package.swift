// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "DBPlaygroundApp",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(name: "DBPlaygroundApp", path: "Sources/DBPlaygroundApp")
    ]
)
