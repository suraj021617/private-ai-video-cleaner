# Desktop packaging

Windows packaging helpers for Private AI Video Cleaner.

## Portable mode

```powershell
cd desktop/scripts
.\package-portable.ps1
.\build-windows-installer.ps1 -PortableOnly
```

Creates `desktop/dist/PrivateAIVideoCleaner/` with:

- `Start-PrivateAIVideoCleaner.bat`
- `portable.config.json` (local storage/models + auto-update feed stub)
- backend app sources and docs

## Windows installer

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
.\package-portable.ps1
.\build-windows-installer.ps1
```

Produces `desktop/dist/installer/PrivateAIVideoCleaner-<version>-Setup.exe` with a desktop shortcut.

## Auto update

`portable.config.json` includes an `autoUpdate.feedUrl` stub. Wire the feed to a signed release manifest in production; the launcher checks it on start when `enabled` is true.
