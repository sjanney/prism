#!/bin/bash
# Download a tiny subset of images for testing Prism

mkdir -p data/sample
cd data/sample

echo "--- 📥 Downloading Sample Dataset ---"
# Using some public domain / placeholder images for now
# In a real scenario, this would point to a specific NuScenes mini-blob
curl -L -o sample1.jpg https://raw.githubusercontent.com/sjanney/prism/main/docs/sample1.jpg || touch sample1.jpg
curl -L -o sample2.jpg https://raw.githubusercontent.com/sjanney/prism/main/docs/sample2.jpg || touch sample2.jpg

echo "--- ✅ Done ---"
echo "You can now index this folder: $(pwd)"
