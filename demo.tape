# Prism Demo Recording
# Creates a GIF showing the core workflow: launch → index → search

Output assets/prism_demo.gif

# Terminal settings for crisp output
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms
Set Padding 20

# Start Prism (backend should already be running)
Hide
Type "cd /Users/shanejanney/autonomous-vechicle-vlm && ./run_prism.sh"
Enter
Sleep 8s
Show

# Wait for the app to load
Sleep 3s

# Navigate to Index New Data
Type "j"
Sleep 300ms
Type "j"
Sleep 300ms
Enter
Sleep 1s

# Type sample data path
Type "data/sample"
Sleep 500ms
Enter

# Wait for indexing to complete
Sleep 5s

# Go back to dashboard and navigate to Search
Tab
Sleep 1s
Tab
Sleep 500ms

# Type a search query
Type "car"
Sleep 500ms
Enter

# Wait for results
Sleep 3s

# Navigate through results
Type "j"
Sleep 500ms
Type "j"
Sleep 500ms

# Open a result
Enter
Sleep 2s

# Final pause
Sleep 2s

# Exit
Ctrl+C
