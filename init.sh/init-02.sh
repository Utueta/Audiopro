#!/bin/bash
#"""
#Audiopro v0.3.1
#Handles the automated directory structure creation and package initialization.
#"""
PROJECT_NAME="Audiopro"
directories=(
    "$PROJECT_NAME/core/analyzer"
    "$PROJECT_NAME/core/brain/weights"
    "$PROJECT_NAME/persistence"
    "$PROJECT_NAME/ui/components"
    "$PROJECT_NAME/database"
    "$PROJECT_NAME/logs"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
done

# Initialize Python Packages
find "$PROJECT_NAME" -type d -exec touch {}/__init__.py \;
echo "Audiopro v0.3.1 Structure Initialized."
