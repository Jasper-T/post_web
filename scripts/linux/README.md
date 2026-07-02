# Linux release scripts

These scripts mirror the Windows PowerShell release flow for Linux.

Recommended location:

```bash
scripts/release/linux/
```

Run from the project repository:

```bash
cd scripts/release/linux
chmod +x *.sh
./release.sh
```

Common options:

```bash
./release.sh --project-name web-post
./release.sh --onefile
./release.sh --onedir
./release.sh --no-frontend-build
./release.sh --filesystem-root /mnt/data
```

Output defaults to:

```bash
release/linux/web-post/
```

Run the packaged app:

```bash
release/linux/web-post/web-post
# or
release/linux/web-post/start.sh
```

Requirements:

- Linux x86_64 or the same architecture you want to package for
- `bash`
- `uv`
- Python dependencies defined by `uv sync --group release`
- Node.js and `npm`
- PyInstaller available in the release group

Note: PyInstaller builds are not cross-platform. Build the Linux package on Linux.
