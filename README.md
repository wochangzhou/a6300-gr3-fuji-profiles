# 让索尼 A6300 拍出理光、富士、哈苏的颜色

这是一套给 **Lightroom Classic / Camera Raw** 用的「配置文件」和「预设」，专门给 **Sony A6300（ILCE-6300）** 的 RAW 照片用。装好之后，在 Lightroom 里点一下，就能把 A6300 的照片换成下面这些相机的味道：

| 风格组 | 包含 | 适合 |
|---|---|---|
| **A6300 理光模拟** | GR III / GR IV 的 Standard、Positive Film（正片）、Negative Film（负片）、Vivid（鲜艳）、三种黑白 | 街拍、日常扫街 |
| **A6300 富士模拟** | Classic Chrome、Classic Neg、Provia、Velvia、Astia、Eterna、Nostalgic Neg、Reala Ace 等 11 种胶片模拟 | 喜欢富士色调的人 |
| **A6300 哈苏模拟** | Hasselblad Standard、Hasselblad Nature | 想要哈苏 X2D 那种自然、通透的颜色 |

> ⚠️ 只对 **A6300 拍的 RAW（.ARW）** 有效。JPG 和其他相机的照片在列表里看不到这些风格。

---

## 一、先搞懂两个词

- **配置文件（Profile）**：决定照片「底色」的东西，相当于换了一台相机的成像风格。在 Lightroom「修改照片」面板最上面，「配置文件」那一栏里选。
- **预设（Preset）**：一键套用的设置。这里的预设只做一件事：帮你选好对应的配置文件。在左边「预设」面板里点。

两种方式效果一样，哪个顺手用哪个。

---

## 二、怎么得到安装包

因为版权原因（配置文件是用 Adobe 自带的文件计算出来的），这个仓库**不直接提供做好的文件**，需要在你自己的电脑上「生成」一次。不用怕，只要复制粘贴几行命令。

**需要：**
- 一台 Mac
- 已经装好 Lightroom Classic
- 能上 GitHub

**步骤：**

1. 打开「终端」（启动台 → 其他 → 终端，或者按 ⌘ + 空格 搜索「终端」）。
2. 复制下面这行，粘贴进终端，按回车。第一次可能会弹窗让你安装「命令行开发者工具」，点「安装」，装完再重新运行这一行：

   ```bash
   git clone https://github.com/wochangzhou/a6300-gr3-fuji-profiles.git ~/a6300-profiles
   ```

3. 再复制这一行，回车，等它跑完（一两分钟，最后会显示 `Done`）：

   ```bash
   cd ~/a6300-profiles && ./build.sh
   ```

4. 打开生成好的文件夹：

   ```bash
   open ~/a6300-profiles/build/export
   ```

   里面有 4 个压缩包：

   - `A6300 GR III Profiles.zip`：理光 GR III
   - `A6300 GR IV Profiles.zip`：理光 GR IV
   - `A6300 Fujifilm Simulation.zip`：富士
   - `A6300 Hasselblad.zip`：哈苏

   想要哪个就装哪个，全装也没问题。

> 用 Windows？目前生成步骤只支持 Mac。可以找一位有 Mac 的朋友帮你生成，把压缩包发给你，安装方法见下面。

---

## 三、安装

每个压缩包解压后都有两个文件夹：`CameraProfiles` 和 `Settings`，还有一份 `安装说明.txt`。

1. 在访达里按 **⌘ + Shift + G**，粘贴下面的地址，回车：

   ```
   ~/Library/Application Support/Adobe/CameraRaw/
   ```

   （Windows 是 `C:\Users\你的用户名\AppData\Roaming\Adobe\CameraRaw\`）

2. 把压缩包里 **`CameraProfiles` 里面的文件**，复制到这里的 `CameraProfiles` 文件夹。
3. 把压缩包里 **`Settings` 里面的文件夹**，复制到这里的 `Settings` 文件夹。
   - 没有这两个文件夹的话，自己新建一个，名字要一模一样。
   - 提示「已有同名文件」时选「替换」。
4. **完全退出 Lightroom，再重新打开。**

---

## 四、使用

1. 在 Lightroom 里选一张 **A6300 拍的 RAW**，进入「修改照片」。
2. 两种用法，选一种：
   - **配置文件**：点右侧面板顶部「配置文件」旁边的四个小方块图标，打开配置文件浏览器，找到「A6300 理光模拟」「A6300 富士模拟」或「A6300 哈苏模拟」，点一下就生效。
   - **预设**：在左侧「预设」面板里找到同名的组，点一下就生效。
3. 套用后，曝光、白平衡这些照常调就行。

**小建议：**
- 拍 RAW，白平衡拍完再调都可以。
- 理光的 Positive Film、Vivid 比较浓，阳光下的红色可能会「溢出」，适当降一点饱和度就好。
- 想要理光 GR 那种四角压暗？在「效果」里加一点暗角。

---

## 五、常见问题

**装了但列表里找不到？**
- 确认是 **A6300 的 RAW**，JPG 不行，其他相机也不行。
- 确认文件放对了地方：`.dcp` 文件在 `CameraProfiles` 里，预设文件夹在 `Settings` 里。
- 确认已经**完全退出并重启**了 Lightroom。

**`./build.sh` 报错说找不到 Lightroom？**
Lightroom Classic 必须装在默认位置（「应用程序」文件夹）。如果你只装了 Photoshop 的 Camera Raw，可以这样指定位置后再运行：

```bash
LR_PROFILES="/Library/Application Support/Adobe/CameraRaw/CameraProfiles" ./build.sh
```

**仓库更新了，我怎么升级？**

```bash
cd ~/a6300-profiles && git pull && ./build.sh
```

然后按「安装」步骤重新复制一遍，选「替换」。

**这样就和真的理光、富士、哈苏一模一样了吗？**
不是。这是把这些相机的「风格」搬到 A6300 上，颜色会非常接近，但不同的感光元件天生有差别，不可能 100% 一样。可以理解为「A6300 版的理光 / 富士 / 哈苏味」。

**能卸载吗？**
到上面那两个文件夹里，把对应的 `.dcp` 文件和预设文件夹删掉，重启 Lightroom 就行。

---

## 想了解原理？

颜色是怎么算出来的、用了哪些数据、精度有多少，都写在 **[技术说明](docs/技术说明.md)** 里。

## 致谢与版权

- 富士胶片模拟来自 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation)（源自 abpy/FujifilmCameraProfiles），生成时会自动下载。
- 理光、哈苏风格基于 Adobe 随 Lightroom 附带的配置文件计算，所以仓库不直接分发 `.dcp` 文件，要用你自己电脑上的 Lightroom 生成。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
