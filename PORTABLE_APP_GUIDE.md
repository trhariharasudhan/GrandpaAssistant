# Portable App Guide

## Built App

After running [build_react_desktop.cmd](/C:/Users/ASUS/OneDrive/Desktop/GrandpaAssistant/build_react_desktop.cmd), the portable app is created here:

- [Grandpa Assistant 0.1.0.exe](/C:/Users/ASUS/OneDrive/Desktop/GrandpaAssistant/frontend/release/Grandpa%20Assistant%200.1.0.exe)

## Quick Setup

Create a desktop shortcut:

```powershell
setup_portable_desktop.cmd
```

Create desktop shortcut and enable startup launch:

```powershell
setup_portable_desktop.cmd /startup-on
```

Remove startup launch:

```powershell
setup_portable_desktop.cmd /startup-off
```

## Normal Use

1. Double-click the desktop shortcut.
2. Use `Text` or `Voice` mode inside the app.
3. Keep the backend/startup scripts only for development. The portable app is the end-user path.
