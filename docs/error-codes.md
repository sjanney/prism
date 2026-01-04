# Prism Error Codes

This document lists all error codes you may encounter when using Prism, along with their causes and solutions.

---

## Error Code Format

All Prism error codes follow the format: `PSM-XXXX`

| Prefix | Category |
|--------|----------|
| `PSM-1XXX` | Connection / Network Errors |
| `PSM-2XXX` | Model / AI Errors |
| `PSM-3XXX` | Database Errors |
| `PSM-4XXX` | File System Errors |
| `PSM-5XXX` | License / Pro Errors |

---

## Connection Errors (PSM-1XXX)

### PSM-1001: Backend Connection Failed

**Message:** `rpc error: code = Unavailable desc = connection refused`

**Cause:** The TUI cannot connect to the Python backend server.

**Solutions:**
1. Ensure the backend is running. Check `backend.log` for errors.
2. Run `./run_prism.sh` which starts both backend and frontend.
3. Check if port 50051 is blocked or in use:
   ```bash
   lsof -i :50051
   ```

---

### PSM-1002: Backend Timeout

**Message:** `rpc error: code = DeadlineExceeded desc = context deadline exceeded`

**Cause:** A request took longer than the timeout allows. This often happens on first search when models are loading.

**Solutions:**
1. **First search is slow:** This is expected. The first search loads ~1.5 GB of model weights. Wait up to 30 seconds.
2. **Subsequent searches slow:** Check GPU availability. CPU-only inference is much slower.
3. Increase timeout in `frontend/main.go` (search: `WithTimeout`).

---

## Model Errors (PSM-2XXX)

### PSM-2001: Model Loading Failed

**Message:** `Failed to load SigLIP model` or `Failed to load YOLOv8 model`

**Cause:** Model weights could not be downloaded or loaded.

**Solutions:**
1. Check your internet connection (first run downloads models).
2. Check disk space (~2 GB required for models).
3. Check HuggingFace cache: `~/.cache/huggingface/`
4. Try manually downloading:
   ```python
   from transformers import SiglipModel
   SiglipModel.from_pretrained("google/siglip-so400m-patch14-384")
   ```

---

### PSM-2002: CUDA Out of Memory

**Message:** `CUDA out of memory`

**Cause:** GPU doesn't have enough VRAM for the model.

**Solutions:**
1. Close other GPU-intensive applications.
2. Use a smaller batch size (future feature).
3. Fall back to CPU by setting `CUDA_VISIBLE_DEVICES=""`:
   ```bash
   CUDA_VISIBLE_DEVICES="" ./run_prism.sh
   ```

---

## Database Errors (PSM-3XXX)

### PSM-3001: Dimension Mismatch

**Message:** `all input arrays must have the same shape` or `Model dimension mismatch`

**Cause:** Your database contains embeddings from a different model version with different vector dimensions.

**Solutions:**
1. Delete the old database and re-index:
   ```bash
   rm prism.db
   ./run_prism.sh
   # Then re-index your data
   ```
2. Or back it up first:
   ```bash
   mv prism.db prism.db.bak
   ```

---

### PSM-3002: Database Locked

**Message:** `database is locked`

**Cause:** Another process is using the database.

**Solutions:**
1. Close any other Prism instances.
2. Kill stale backend processes:
   ```bash
   pkill -f "python.*server.py"
   ```

---

### PSM-3003: Database Not Found

**Message:** `No database connected` or `prism.db not found`

**Cause:** No database file exists at the expected path.

**Solutions:**
1. Index some data first—the database is created on first index.
2. Or connect to a specific database via "Connect Database" in the TUI.

---

## File System Errors (PSM-4XXX)

### PSM-4001: Path Not Found

**Message:** `Path not found: /some/path`

**Cause:** The folder path you entered doesn't exist.

**Solutions:**
1. Use the native folder picker (press `o` in Index view).
2. Ensure the path is absolute, not relative.
3. Check for typos.

---

### PSM-4002: No Images Found

**Message:** `Found 0 images to index`

**Cause:** The folder contains no supported image files.

**Solutions:**
1. Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.webp`
2. Prism searches recursively—ensure images exist in subfolders.

---

### PSM-4003: Permission Denied

**Message:** `Permission denied`

**Cause:** Prism cannot read the folder or files.

**Solutions:**
1. Check file permissions: `ls -la /path/to/folder`
2. On macOS, grant Terminal "Full Disk Access" in System Preferences.

---

## License Errors (PSM-5XXX)

### PSM-5001: Invalid License Key

**Message:** `Invalid license key. Keys start with 'PRISM-PRO-'`

**Cause:** The entered license key format is incorrect.

**Solutions:**
1. Ensure your key starts with `PRISM-PRO-`.
2. Check for extra spaces or characters.
3. Contact support if you believe your key is valid.

---

### PSM-5002: Free Version Limit Reached

**Message:** `Free version limit (5000 images). Upgrade to Pro for unlimited.`

**Cause:** You've exceeded the 5,000 image limit on the free version.

**Solutions:**
1. Upgrade to Prism Pro for unlimited indexing.
2. Or index a smaller subset of your data.

---

## Still Having Issues?

1. Check `backend.log` for detailed Python errors.
2. Open an issue on [GitHub](https://github.com/sjanney/prism/issues).
3. Include your error code, OS, and Python/Go versions.
