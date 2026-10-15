# 操作说明

## 选择环境

先查看 Bottles 的真实路径、runner 和程序，不凭默认目录猜测：

```sh
flatpak run --command=bottles-cli com.usebottles.bottles info bottles-path
flatpak run --command=bottles-cli com.usebottles.bottles list bottles
flatpak run --command=bottles-cli com.usebottles.bottles programs -b MyApp
```

需要新 Bottle 时，先运行 `bottles-cli new --help`，按当前版本选择独立名字和 application 环境。已有环境先保存程序并备份。脚本接受明确的 prefix 和 Wine 可执行文件；宿主依赖齐全时优先直接使用该 runner；只有确实需要 Flatpak runtime 时加 `--flatpak`。多个任务共用 Flatpak 应用状态，生命周期操作可能同时影响其他 prefix；不得使用全局 `flatpak kill`，服务退出后必须重新读取真实窗口。它直接调用 runner，不会完整执行 Bottles 的每应用启动配置；需要 DXVK、DLL overrides 或环境变量时核对并显式传入，或使用 Bottles 自己的 `run`。

Wine 初次初始化可能花较长时间；先等初始化结束，再启动 UI helper。不要同时创建同一个 prefix。初次初始化可能出现 Mono/Gecko 下载提示；先真实截图查看，再决定取消或按应用需求安装，不能把等待提示误判为进程已就绪。没有 X display 的终端不是可用 GUI 会话。

## 私有桌面

```sh
python3 scripts/winapp.py --display :42 desktop --state .local/display-42
# Xvfb 可用时：增加 desktop 子命令参数 --backend xvfb
```

`ready.json` 出现后才算就绪。显示号须未被其他程序占用；不使用 `-ac`，不监听 TCP。Cage 使用有效的用户 XDG_RUNTIME_DIR，缺省尝试 `/run/user/<uid>`。读取实际 geometry，不能把请求尺寸当作截图尺寸。

后续示例用 shell 数组保存共同参数，避免空格和括号被拆开：

```bash
opts=(--prefix /path/to/prefix --wine /path/to/runner/bin/wine
      --display :42 --xauthority .local/display-42/Xauthority)
# Bottles Flatpak runner 时：opts+=(--flatpak)
python3 scripts/winapp.py "${opts[@]}" install --exe /path/to/official-installer.exe
python3 scripts/winapp.py "${opts[@]}" install --exe /path/to/official-installer.msi -- /qn
python3 scripts/winapp.py "${opts[@]}" launch --exe '/path/to/prefix/drive_c/Program Files/App/App.exe'
```

安装包从厂商官网下载；记录来源和散列。静默参数必须查该安装器文档，不通用推测。脚本把安装包/helper 按内容散列复制到本 prefix 的 drive_c；不会开放整个宿主目录给 Flatpak。安装器子进程结束顺序因软件而异，命令返回后仍要验证安装文件与实际窗口。

## 控件

```sh
python3 scripts/winapp.py "${opts[@]}" ui snapshot --helper .local/winui.exe
python3 scripts/winapp.py "${opts[@]}" ui text --helper .local/winui.exe   --hwnd HWND --pid PID --started STARTED --value 'Verified input'
python3 scripts/winapp.py "${opts[@]}" ui click --helper .local/winui.exe   --hwnd HWND --pid PID --started STARTED
python3 scripts/winapp.py "${opts[@]}" ui select --helper .local/winui.exe   --hwnd HWND --pid PID --started STARTED --index 1
```

HWND / PID / STARTED 必须来自刚取得的同一控件快照。文本可能截断到 2047 个 UTF-16 单元；`text_readable=false` 表示超时或不可读，不表示字段为空。`accepted=true` 仅证明消息接受，必须刷新快照并验证保存文件或软件状态。不要把密码放在命令行，系统进程列表和日志可能记录参数。

`menu` 读取原生菜单，`command --id` 只调用实际观察到的命令；无菜单不代表没有功能。自绘 TreeView/ListView 数据不能靠普通 WM_GETTEXT 读取，不支持的操作不编造成功。

```sh
python3 scripts/winapp.py screenshot --state .local/display-42 --output .local/verified.png
```

截图只支持脚本创建且进程仍存活的私有桌面。必须打开图片检查。保存和正常关闭应用后，在对应 desktop 终端 Ctrl-C。不要全局 `pkill wine` 或关闭他人的显示服务。

## 官方依据

- [Bottles CLI](https://docs.usebottles.com/advanced/cli)
- [Win32 SendMessageTimeoutW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw)
- [Cage 源码与用法](https://github.com/cage-kiosk/cage)
- [Xvfb 文档](https://www.x.org/releases/current/doc/man/man1/Xvfb.1.xhtml)
