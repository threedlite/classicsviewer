// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ClassicsViewer",
    platforms: [
        .iOS(.v26)
    ],
    products: [
        .library(
            name: "ClassicsViewer",
            targets: ["ClassicsViewer"]),
    ],
    dependencies: [
        .package(url: "https://github.com/stephencelis/SQLite.swift.git", from: "0.14.1"),
        .package(url: "https://github.com/weichsel/ZIPFoundation.git", from: "0.9.0")
    ],
    targets: [
        .target(
            name: "ClassicsViewer",
            dependencies: [
                .product(name: "SQLite", package: "SQLite.swift"),
                .product(name: "ZIPFoundation", package: "ZIPFoundation")
            ],
            path: ".",
            exclude: ["Package.swift", "Resources"],
            sources: [
                "ClassicsViewerApp.swift",
                "Database",
                "Models",
                "ViewModels",
                "Views",
                "Utilities"
            ]
        ),
        .testTarget(
            name: "ClassicsViewerTests",
            dependencies: ["ClassicsViewer"],
            path: "Tests"
        ),
    ]
)