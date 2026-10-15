---
name: linux-windows-apps
description: Install, launch, inspect and control Windows desktop applications on Linux using explicit Bottles or Wine prefixes, native Win32 controls and optional background virtual desktops. Use for Windows app installation, GUI automation and compatibility diagnosis on Linux.
---

# Windows applications on Linux

Use an application-specific Bottles/Wine prefix. The scripts are relative to this skill directory; run `python3 scripts/winapp.py --help` for commands. Read [setup and operation](references/operation.md) when choosing a backend or installing software, and [compatibility diagnosis](references/compatibility.md) for fonts, WebView2 or inaccessible controls.

## Establish a real session

1. Inspect the selected prefix, installed Wine runner, application executable and live processes. Preserve existing libraries, licenses and unsaved work. Installation authorization does not authorize purchases, trial enrollment or license acceptance beyond the user's stated scope.
2. Use `doctor` before installing dependencies. Select the actual Bottles runner, not whichever `wine` happens to be on PATH. Every execution requires `--prefix`; never let Wine silently use `~/.wine`. Download installers from the publisher and record the source and SHA-256. Wine and Bottles are compatibility tools, **not security sandboxes**; Wine's Z: drive can expose host files.
3. If foreground interaction would interrupt the user, start a new private display with `desktop`. Prefer Xvfb where available; the included Cage/Xwayland backend also works on a Wayland host. Run it in a separate persistent terminal. Read its `ready.json`, and pass its display and Xauthority to subsequent commands. Do not reuse a display belonging to another task. A prefix already running on another display must be saved and closed before moving it.
4. Install with `install`, then `launch` the installed executable. Prefer the selected runner directly on the host when its dependencies are present. `--flatpak` is an optional fallback inside `com.usebottles.bottles`; concurrent invocations share application lifecycle state. Never run `flatpak kill com.usebottles.bottles` or global Wine cleanup while other tasks are active. Installer exit status and installed files alone do not prove the GUI works.

## Observe, act, verify

Build the helper with `build-helper`, then `ui snapshot`. The snapshot contains real HWNDs, Windows process IDs and process creation timestamps. Scope actions using **all three** from a fresh snapshot: `--hwnd`, `--pid`, `--started`. HWNDs and PIDs can be reused; refresh after dialogs, restarts and delayed operations.

- `ui text --value …`: ordinary Edit/RichEdit fields. Do not put credentials in command arguments or transcripts. Password controls are redacted in snapshots and refused by this command.
- `ui click`: native Button controls; `ui select --index N`: native ComboBox controls. No global pointer movement or focus activation is required. Custom-drawn applications may ignore these messages.
- `ui menu` observes native menu command IDs; `ui command --id N` invokes an **observed** command. An accepted message is not proof of a completed action.
- `ui close`: request normal window closure; save prompts may remain. There is no blanket process-kill command.

After every consequential action, refresh the UI and verify the actual result: a file, application state, reopened document or native export. Report installation, startup, imports, edits and saved output separately. Do not edit an application's internal database and call that a GUI operation.

`screenshot` captures only a private display created by `desktop`. View the image before using it as evidence; a black, stale or cropped capture is not success. Capture existing user windows only through an appropriately scoped available tool. Never publish unrelated desktop content, personal data or licensed software files.

## Limits and fallback

This helper targets traditional Win32 controls. WebView, Electron, owner-drawn lists and remote applications may need UI Automation, application scripting or screenshot-based interaction. Use available, authorized tools and actual observations; do not infer controls from stale screenshots. Stop after a repeatable compatibility failure and report the failing layer instead of installing unrelated runtimes indefinitely. In particular, WebView2 version detection is not proof its browser process renders successfully.

Keep changes reversible: back up the selected prefix before runner, registry or font changes; preserve original executables. Do not patch activation, bypass challenges or fabricate screenshots. For a repository-local smoke test, use `examples/control-demo.c`, which contains only synthetic data.
