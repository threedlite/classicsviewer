#!/bin/bash

cd /Users/user1/git/classicsviewer/ios/ClassicsViewer

# Generate Xcode project from Package.swift
swift package generate-xcodeproj

# Move the generated project up one level
if [ -f "ClassicsViewer.xcodeproj/project.pbxproj" ]; then
    mv ClassicsViewer.xcodeproj ../
    echo "Xcode project generated successfully at ios/ClassicsViewer.xcodeproj"
else
    echo "Failed to generate Xcode project"
    exit 1
fi