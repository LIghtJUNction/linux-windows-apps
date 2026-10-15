# 实际验证

2026-10-16，Linux Wayland 主机，Cage + Xwayland 1280×720 私有显示，Bottles 安装的 soda-11.0-10 runner **直接在宿主执行**，独立测试 prefix。

## 已通过

- `unittest` 5 项：拒绝隐式 prefix、路径和空格/元字符原样传递、散列分阶段复制及篡改拒绝、私有显示 PID 重用拒绝、不调用 shell 解释参数。
- MinGW-w64 构建 32 位和 64 位控件 helper，开启 `-Wall -Wextra -Werror`。
- 自有原生 Win32 demo：32 位与 64 位 helper 分别读取窗口、写入普通文本、选择 ComboBox、点击 Button，并重新读取实际状态字段确认更新。
- 同一真实窗口上的密码框隐藏/拒写，错误进程创建时间被拒绝。
- 厂商来源 7-Zip 26.04 x86 安装器，经 `install -- /S` 安装，实际启动 `7zFM.exe`，读取到 `7-Zip::FM` 主窗口并查看截图。

7-Zip 来源：[官方下载页](https://7-zip.org/download.html)，链接至 `ip7z/7zip` GitHub release。实际安装包 SHA-256：`39bf65045153fc26c42fa9fe47afd8cd1b11671c7f11d031e738c9a13960c009`。安装包不分发到本仓库。

`demo.png` 是实际后台桌面的合成数据应用截图，非绘制的界面。它仅证明上述 demo 操作，不证明任何其他软件的功能完成。

## 实测限制

同一主机多个并行任务使用 Bottles Flatpak 时，出现 Wine server 退出、缓存窗口仍可见、下一次句柄校验拒绝的现象。没有足够证据确认唯一根因。改为直接执行 host runner 后，上述完整控件检查通过。不要依据缓存截图继续操作；必须以活窗口和实际保存结果为准。

MSI 入口已实现但本次未进行真实 MSI 安装验证。WebView2、Office/EndNote Word 插件、自绘控件、中文字体安装和 Xvfb 后端没有在本次开源 demo 中完成验收，不能宣称已支持全部 Windows 软件。中文字体和 WebView2 只提供排查指导。

复现原生 demo：

```sh
i686-w64-mingw32-gcc -std=c11 -Wall -Wextra -Werror -municode -mwindows \
  examples/control-demo.c -o /selected/prefix/drive_c/control-demo.exe -luser32 -lgdi32
# 先按 operation.md 启动私有桌面、helper 与 demo，再执行：
python3 tests/native_smoke.py --prefix /selected/prefix --wine /selected/runner/bin/wine \
  --display :42 --xauthority /selected/display/Xauthority --helper .local/winui.exe
```

不触碰其他任务的 prefix 或显示服务；关闭本 demo 后才结束对应私有桌面。
