# A6300 理光 GR III·GR IV / 富士胶片模拟 / 哈苏 Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 和 GR IV 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并在 Adobe Standard 下按 dpreview 影棚 RAW 色卡做色相/饱和度对齐。
- **A6300 富士模拟**：直接使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的 A6300 底片和富士 LUT（上游原版），只改分组名。
- **A6300 哈苏模拟**：Hasselblad Standard 和 Nature，以哈苏 X2D 的 Phocus 输出为准。Standard 用 X2D 的“Lightroom Adobe Standard → Phocus Standard”同机配对（含 Phocus 色调曲线），Nature 用 X2D 的“Phocus Standard → Phocus Nature”同机配对，叠到 Standard 上。

定位：这是**基于 Adobe 配置文件的风格移植**，不是对理光、富士或哈苏机内色彩的复刻。仓库只包含生成流程、测量数据、本项目拟合的表和文档；配置文件由 `build.sh` 用你本机的 Lightroom 和上游仓库生成（见“版权说明”）。

## 快速开始

需要 macOS、Lightroom Classic（或用 `LR_PROFILES` 指向 Camera Raw 的 CameraProfiles 目录）、python3、git。构建不需要第三方 Python 库。

```bash
./build.sh            # 输出到 ./build/export
```

生成四个 zip 包（GR III、GR IV、富士、哈苏），每个包里附有安装说明：把文件复制到 `~/Library/Application Support/Adobe/CameraRaw/` 下的 `CameraProfiles` 和 `Settings`，然后重启 Lightroom。打开 A6300 的 RAW 后，配置文件浏览器和预设面板里会出现 “A6300 理光模拟”、“A6300 富士模拟”、“A6300 哈苏模拟” 三组。

## DCP 渲染顺序

```
相机 RGB ─白平衡→ ─ForwardMatrix→ XYZ D50 → ProPhoto 线性
        ─HueSatMap→ 基础颜色 ─曝光（BaselineExposure + 偏移，截断到 1）→ LookTable（风格）→ ToneCurve → 输出
```

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出），所以所有 LookTable 都用 3D 表（理光 90×32×16，哈苏 90×16×16）。检查脚本另外实现了 SDK 的保色相 RGB 色调曲线。

## 原则：风格差值只在同一台相机上计算

dpreview 影棚不同年份、不同机型的拍摄批次，灯光、色卡版本和曝光都不一样（例如 2016 年那批的 A6300 比后来的 GR III、X-S10 那批亮，GR IV 那批换成了 Calibrite 色卡）。所以“Adobe Standard → 风格”的差值只在目标相机自己身上计算，再接到 A6300 自己的 Adobe Standard 上：

- 理光：差值由 Adobe 的 GR DCP 逐节点精确计算，不用照片。
- 富士：用上游原版。
- 哈苏：Standard 用同一张 X2D RAW 的 Lightroom Adobe Standard 导出和 Phocus Standard 导出配对；Nature 用同一张 X2D RAW 的 Phocus Standard 和 Phocus Nature 导出配对。

理光另外做一层**跨机色卡对齐**，处理 A6300 和 GR 的 Adobe Standard 对同一张色卡给出的颜色差别。这一层修色相、饱和度和明度。曝光先按白块归一化，所以明度比是按颜色的：GR 的暖色块比 A6300 暗约 5–9%（灰阶一致）。早先不修明度时，A6300 上红、橙、肤色、棕等暖色比 GR 原机亮 GR IV +3～+5 L*、GR III +1.4～+4 L*，实拍看起来红色附近亮了一块；修上后与原机差多在 ±1 L* 以内（按 DNG 参考流程模拟 Adobe 的 GR Camera 风格对比）。修正里同样可能混有批次差异，这是实拍对比后的取舍。

## 理光 GR III / GR IV

1. **风格移植**（`scripts/port.py`）：以 GR 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间。对新 LookTable 的每个节点，迭代反解对应的 GR 相机 RGB（不截断负值），用 Adobe 的 GR 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。节点输入是已乘曝光的基础颜色。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（GR III +0.55，GR IV +0.5）和 DefaultBlackRender 沿用 GR 原版。最后一个参数选机型（`"GR III"` 或 `"GR IV"`）；用 3000 个随机颜色检查移植误差（sRGB 编码下最大约 0.06–0.08，主要在高饱和边缘）。饱和度轴用 32 个节点：GR 的 Adobe Standard 基础颜色到 Camera 风格的映射在饱和度约 0.8 处有一个急拐（橙、橙黄、黄正好在这里），16 个节点时插值会把这些颜色的 C* 压低约 4–8。
2. **RAW 测量**：`scripts/raw/decode.py`（rawpy/LibRaw）只做去马赛克，得到线性相机 RGB。`scripts/raw/extract.py` 取 24 色卡每块中心 60×60 像素的均值；`scripts/raw/wheel.py` 在色轮的 12 个扇区 × 4 圈取 48 个点，作为**独立验证集**。结果在 `data/raw/`（A6300、GR III、GR IV）。
3. **基础颜色**（`scripts/rawbase.py`）：用灰块求相机中性点，按 DNG SDK 的方式迭代估计色温，在两组标定之间插值，再经各自的 Adobe Standard ForwardMatrix → ProPhoto → HueSatMap 得到基础颜色。曝光在 HueSatMap 之前按白块归一化。
4. **跨机对齐**（`scripts/rawfit.py`、`scripts/gr/rawmatch.py`）：A6300 → GR 的色相差、饱和度比分别用（色相 × 饱和度）核回归建模，核宽和收缩强度用色卡留一法选择；近中性色（饱和度 <0.15）逐渐不修。每个 LookTable 节点先按模型把 A6300 基础颜色的色相、饱和度和明度转到 GR 的位置，再查移植后的 GR 风格表。

色卡留一法 / 色轮（独立）结果（`rawfit.py` 输出，色相单位为度，饱和度为对数比）：GR III 色相 2.17 → 1.64 / 3.82 → 3.07，饱和度 0.041 → 0.019 / 0.151 → 0.127；GR IV 色相 3.46 → 2.59 / 4.39 → 3.77，饱和度 0.058 → 0.052 / 0.185 → 0.162。

## 富士底片

上游原版 `Sony ILCE-6300 Adobe Standard Linear.dcp` 和 22 个 LUT XMP，不加颜色表，不加曝光偏移。

## 哈苏（`scripts/fit/hasselblad/paired/`）

以哈苏 X2D 的 Phocus 输出为准。只在哈苏自己身上学差异：同一张 X2D RAW 的两份导出逐像素配对，差异只来自渲染（同一帧、同一张色卡、同一种光）。A6300 的颜色不和任何哈苏照片直接拟合，也不用 A6300 的照片取样：颜色表的每个节点都由 DCP 的计算直接构造。

渲染顺序：白平衡 → ForwardMatrix 和 HueSatMap（都是 A6300 的 Adobe Standard 原版）→ BaselineExposureOffset 0 → LookTable（90×32×32）→ 色调曲线（Standard 为 Phocus 灰阶曲线，Nature 在其上叠加 Phocus Nature 的反差）。不带 DefaultBlackRender，与 Adobe Standard 一样用默认的 Auto 黑位处理（Phocus 曲线是相对开着 Auto 的 Adobe Standard 导出测得的；设成 None 时暗部和中灰会亮约 1 L*）。理光移植版保留 None，与 Adobe 的 GR Camera 配置文件一致。

### 导出要求

同一张 X2D RAW：Lightroom 导出 Adobe Standard（ProPhoto 16 位 TIFF），Phocus 导出 Standard 和 Nature（Adobe RGB 16 位 TIFF）。白平衡都点色卡灰块，镜头校正都关闭，中灰在导出时对齐（Adobe Standard N5 L* 45.4，Phocus Standard 44.2：Phocus 本来就略暗，属于它的色调，保留）。

### 步骤

1. **配对**（`pairs_phocus.py`）：Lightroom Adobe Standard 与 Phocus Standard，逐块校正残余位移后取约 7.9 万个 6×6 平整格。Adobe Standard → Phocus：中性格 ΔE00 1.16，彩色 2.96。
2. **位置效应**（`flatfield.py`）：Phocus 在色调曲线之前对画面做了随位置变化的增益（平场校正），相对 Lightroom 导出边缘更亮、更偏黄（r=0.9 处 R/G/B 增益 1.085/1.055/0.996；中性格 Δb 从中心约 0 到边缘 +2.4）。按中性格建模（对数增益 = 亮度项 + 曲线斜率 × r²/r⁴/r⁶ 多项式），在曲线之前从 Phocus 一侧扣除，扣除后各环带 Δb 在 ±0.5 以内。
3. **色调曲线**（`phocus_tone.py`）：中性格（Adobe Standard C*<3）上 Adobe Standard → Phocus 的 ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = ACR3 默认曲线（Adobe Standard 用的曲线，DNG SDK `kAdobeDefaultCurve`）输出的 L* 加上这个差值：ACR3 L* 33.4/51.3/68.6/81.7/91.9 → 32.9/50.4/67.5/82.6/93.3。写出起点配置文件（A6300 Adobe Standard 的矩阵和 HueSatMap、这条曲线、曝光偏移 0）。
4. **差异模型 g**（`analytic.py` 内）：Adobe Standard Lab → Phocus Lab 的核回归（Lab 分箱取中位差，高斯核加权）。参数用左右半幅交叉验证选定（dpreview 场景左右两边是对称摆放的不同物体，比随机切分更能反映对新物体的推广）：σ = (4, 10, 10)、收缩 λ = 0.02，数据支撑不足处按支撑量渐弱到 0。在没见过的物体上：彩色 ΔE00 2.65（不做 g）→ 1.07，C*>30 → 1.27。
5. **逐节点构造**（`analytic.py`）：对颜色表的每个节点 X（已乘曝光的基础颜色），按 DNG 参考流程算出 A6300 的 Adobe Standard 会把它渲染成什么（Adobe Standard 自己的 LookTable + ACR3 曲线），套上 g 得到 Phocus 目标，再按本配置文件的色调曲线（保色相 RGB 曲线）反解出节点应取的值。不依赖场景取样，整个颜色空间都有定义。稳定化：最亮两层沿用下一层（曲线在白附近太平，反解病态）；幅度上限色相 ±25°、饱和度 ×0.6–1.6、明度 ×0.85–1.15；中性轴不改（灰阶只由曲线决定）；饱和度 0.12 以下渐弱到不改。
6. **单调化**（`monotone.py`）：沿饱和度方向逐个节点（每个区间再检查 3 个中间点），保证渲染出的 C* 不回落；只上调出问题节点的饱和度倍数（约 1% 的节点，最多 ×1.25）。

检验（A6300 dpreview 影棚 RAW 上约 9 万个格子，目标 = g 作用于 A6300 自己的 Lightroom Adobe Standard 导出；ΔE2000 均值；括号内为此前“在格子上拟合颜色表”的版本）：检验彩色 0.87（0.91），中性 1.12（1.09），色轮区域 0.86（1.06），高饱和 s>0.5 0.68（0.92）。约 0.9 是格子目标本身的噪声地板。

压力测试（`stress.py`，合成网格：色相 1° × 饱和度 0.02 × 24 档亮度，与 Adobe Standard 对照）：无亮度反转、无色相顺序颠倒，饱和度反转 0.02%（最大回落 1.1 C*）。超出配对数据的高饱和区（s≥0.85）偏离 Adobe Standard 平均 0.9、最大 12（此前的拟合版本 9.2、最大 56，外推失控）。

### Nature（X2D Phocus Standard → Nature，作为相对 Standard 的差别）

1. **配对**（`nature_pairs.py`）：同一张 X2D RAW 的 Phocus Standard 与 Phocus Nature 导出（同一软件、同尺寸，像素对齐），取约 6 万个平整格。两份的白平衡一致，没有随画面位置的变化。Nature 的反差更大（中性格 ΔL*：暗部 −6，L* 40–60 −2.2，L* 60–80 +2.3，高光 +3.3），彩色更浓（色卡 C* +2～+12），色相基本不变。
2. **色调曲线**（`nature_tone.py`）：中性格的 Nature−Standard ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = Standard 曲线输出的 L* 加上这个差值，保持单调（Standard L* 10/30/50/70/90 → −5.2/−5.0/−1.2/+2.8/+3.4）。
3. **颜色表**：同 Standard 的第 4–6 步，源渲染换成上面做好的 Standard（它自己的 LookTable 和曲线），g 为 Phocus Standard Lab → Phocus Nature Lab（交叉验证：彩色 2.75 → 0.72，C*>30 → 1.33）。饱和度反转 0.11%，集中在接近黑色的深暗部和 s≥0.94。曝光偏移 0。

### 复现步骤

需要：上面三份 X2D 导出（Lightroom Adobe Standard 和 Phocus Standard 转成 `.npy`），ACR3 默认曲线（DNG SDK `kAdobeDefaultCurve`，1025 点文本），本机 Lightroom 的 `Sony ILCE-6300 Adobe Standard.dcp`。参数见各文件开头。

1. Standard：`pairs_phocus.py` → `flatfield.py` → `phocus_tone.py` → `analytic.py`（源为 `as:<Adobe Standard.dcp>:<acr3>`，90 32 32）→ `monotone.py`。
2. Nature：`nature_pairs.py` → `nature_tone.py`（用第 1 步的 Standard）→ `analytic.py`（源为第 1 步的 Standard）→ `monotone.py`。
3. 用 `scripts/export_tables.py` 把结果 DCP 里本项目自己的标签（LookTable、色调曲线、曝光偏移、名称）写进 `data/profiles.json` 和 `data/tables/`，`build.sh` 重建后应与拟合出的 DCP 一致。
4. 检查：`stress.py`。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从带 RGB 曲线的预设切换过来时，曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被 LookTable 推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。
- 哈苏：`scripts/fit/hasselblad/paired/stress.py`（饱和度、亮度、色相单调性，平滑度，sRGB 外溢，数据之外的偏离）。

## 局限

- 风格差值不包含目标相机传感器本身的色彩特性（同色异谱）。理光的色卡对齐只用 18 个彩色块，而且两台相机的样张来自不同批次，修正里会混有批次差异。
- 哈苏的配对只在 dpreview 影棚日光一个光源下做，只用 X2D 一台相机。
- 哈苏的检验集来自同一张照片和同一光源，只能说明对“别的颜色”能推广，不能说明对“别的光源”能推广。
- Positive Film 等高饱和风格会把阳光下的饱和红推出 sRGB 色域，这是 Adobe 的 GR 风格本身的特性。

## 目录

```
build.sh                  一键生成（纯 python3）
scripts/dcp.py            DCP（TIFF/IIRC）读取
scripts/port.py           DNG 查表实现 + GR III / GR IV 风格移植 + DCP 写出
scripts/rawfit.py         A6300 → GR 色相/饱和度修正拟合 + 色轮独立测试
scripts/gr/rawmatch.py    生成对齐后的 GR III / GR IV 配置文件
scripts/groups.py         分组 XMP（含点曲线复位）
scripts/assemble.py       哈苏：本项目的表 + 本机的 A6300 Adobe Standard → DCP
scripts/export_tables.py  从拟合好的 DCP 导出本项目自己的标签到 data/
scripts/rawbase.py        相机 RGB → 各机 Adobe Standard 基础颜色
scripts/raw/              RAW 解码与色卡、色轮取样（需要 rawpy、numpy）
scripts/fit/              哈苏拟合与检查脚本（需要 numpy、rawpy、tifffile 和 dpreview 原图；构建时不运行）
data/raw/                 A6300、GR III、GR IV 色卡与色轮的线性相机 RGB 均值
data/profiles.json, data/tables/  哈苏 Standard/Nature（LookTable、色调曲线、曝光偏移、名称）
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（哈苏的 LookTable、色调曲线），矩阵和 HueSatMap 在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
