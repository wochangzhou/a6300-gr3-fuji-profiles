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

## 哈苏（`scripts/fit/hasselblad/`）

以哈苏 X2D 的 Phocus 输出为准。哈苏只和自己比：同一张 X2D RAW 的两份导出逐像素配对，差异只来自渲染（同一帧、同一张色卡、同一种光），再把这个差异迁移到 A6300 自己的 Adobe Standard 上。A6300 的颜色不和任何哈苏照片直接拟合。

渲染顺序：白平衡 → ForwardMatrix 和 HueSatMap（都是 A6300 的 Adobe Standard 原版）→ BaselineExposureOffset 0 → LookTable（90×16×16，同机配对拟合）→ 色调曲线（Standard 为 Phocus 灰阶曲线，Nature 在其上叠加 Phocus Nature 的反差）。不带 DefaultBlackRender，与 Adobe Standard 一样用默认的 Auto 黑位处理（Phocus 曲线是相对开着 Auto 的 Adobe Standard 导出测得的；设成 None 时暗部和中灰会亮约 1 L*）。理光移植版保留 None，与 Adobe 的 GR Camera 配置文件一致。

### 导出要求

- X2D：同一个 RAW 在 Lightroom 导出 Adobe Standard（ProPhoto 16 位 TIFF），在 Phocus 导出 Standard 和 Nature（Adobe RGB 16 位 TIFF）。白平衡都点色卡灰块，镜头校正都关闭，中灰在导出时对齐（Adobe Standard N5 L* 45.4，Phocus Standard 44.2：Phocus 本来就略暗，属于它的色调，保留）。
- A6300：同一 dpreview 影棚场景的 RAW，Lightroom Adobe Standard 导出（ProPhoto 16 位 TIFF），镜头校正关闭，白平衡点灰块，曝光调到中灰与 X2D 的 Adobe Standard 导出一致（N5 L* 约 45，−0.27 EV）。

### Standard

1. **配对**（`paired/pairs_phocus.py`）：Lightroom Adobe Standard 与 Phocus Standard 两份导出，逐块校正残余位移后取约 7.9 万个 6×6 平整格。Adobe Standard → Phocus：中性格 ΔE00 1.16，彩色 2.96。
2. **位置效应**（`paired/flatfield.py`）：Phocus 在色调曲线之前对画面做了随位置变化的增益（传感器/镜头的平场校正），相对 Lightroom 导出，边缘更亮、更偏黄（r=0.9 处 R/G/B 增益 1.085/1.055/0.996；中性格 Δb 从中心约 0 到边缘 +2.4）。按中性格建模（对数增益 = 亮度项 + 曲线斜率 × r²/r⁴/r⁶ 多项式），在曲线之前从 Phocus 一侧扣除，扣除后各环带 Δb 在 ±0.5 以内。
3. **色调曲线**（`paired/phocus_tone.py`）：中性格（Adobe Standard C*<3）上 Adobe Standard → Phocus 的 ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = ACR3 默认曲线（Adobe Standard 用的曲线）输出的 L* 加上这个差值。Phocus 中间调略暗、高光略亮：ACR3 L* 33.4/51.3/68.6/81.7/91.9 → 32.9/50.4/67.5/82.6/93.3。写出起点配置文件：A6300 Adobe Standard 的矩阵和 HueSatMap、恒等 LookTable、这条曲线、曝光偏移 0。
4. **A6300 取样**（`a6300_cells.py`）：A6300 RAW（`scripts/raw/decode.py` 的线性相机 RGB）在 /2 网格上取 6×6 平整格，算 Adobe Standard 基础颜色（白平衡 → ForwardMatrix → HueSatMap，按白块归一化曝光，与 `rawbase.py` 相同）。RAW 到 Lightroom 导出的位置由逐块配准得到（关闭镜头校正后只差 6 px 平移，残差 0.02 px）。共约 9.2 万格，两个色轮（约 4700 格）不参与训练。
5. **迁移到 A6300**（`paired/synth.py`）：把配对差异（在 Lab 里按颜色核回归，记为 g）作用到 A6300 自己的 Adobe Standard 导出上，得到每个格子的合成目标。只保留 g 有数据支撑的格子。
6. **颜色表**（`paired/pure_correct.py`）：从第 3 步的起点出发拟合合成目标（核回归，按 125px 棋盘格分训练/检验，不做高饱和淡出）。模型曝光 `KMODEL=0.4212`：在这个值下 ACR3 曲线给出的 A6300 色卡灰阶与 A6300 的 Adobe Standard 导出一致（N8–N3.5 平均差 0.36 L*）。幅度上限：色相 ±25°，饱和度 ×0.6–1.6，明度 ×0.85–1.15（实际用到的最大值约 16°、×0.88–1.23、×0.98–1.06）。LookTable 在中性色上不改明度。

检验（ΔE2000 均值，对合成目标；“起点”为恒等 LookTable）：检验彩色 1.00 → 0.90，中性 0.95 → 0.92，色轮区域（未训练）1.13 → 1.06。按模型算，A6300 色卡灰阶与 X2D 的 Phocus 导出在白到 N5 之间相差 ≤0.5 L*。

### Nature（X2D Phocus Standard → Nature，作为相对 Standard 的差别）

1. **配对**（`paired/nature_pairs.py`）：同一张 X2D RAW 的 Phocus Standard 与 Phocus Nature 导出（同一软件、同尺寸，像素对齐），取约 6 万个平整格。两份的白平衡一致：色卡灰阶 Δa、Δb ≤0.35，全图中性格 Δa +0.1～+0.4、Δb −0.3～+0.1，没有随画面位置的变化。Nature 的反差更大（中性格 ΔL*：暗部 −6，L* 40–60 −2.2，L* 60–80 +2.3，高光 +3.3），彩色更浓（色卡 C* +2～+12，橙、黄、绿、中红、紫蓝约 +10），色相基本不变（蓝、青、红 +4～+6°）。
2. **色调和颜色**（`paired/nature_build.py`）：色调 = 中性格的 Nature−Standard ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = Standard 曲线输出的 L* 加上这个差值，保持单调（Standard L* 10/30/50/70/90 → −5.2/−5.0/−1.2/+2.8/+3.4）。颜色 = Lab 核回归 g（与 `synth.py` 同一估计）作用于 Standard 在 A6300 每个格子上的渲染，得到 Nature 目标；再用 `pure_correct.py`（`KMODEL=0.4212`，从 Nature 曲线、恒等 LookTable 出发）拟合颜色表。曝光偏移 0。
3. **结果**：检验彩色 0.71 → 0.38，中性 0.35 → 0.32，色轮区域 0.69 → 0.42。

### 复现步骤

需要：上面“导出要求”里的四份 TIFF（X2D 的 Lightroom Adobe Standard、Phocus Standard、Phocus Nature，A6300 的 Lightroom Adobe Standard，前三份转成 `.npy`），A6300 的 dpreview 日光 RAW，ACR3 默认曲线（DNG SDK `kAdobeDefaultCurve`，1025 点文本）。脚本在 `scripts/fit/hasselblad/`，参数见各文件开头。

1. `paired/pairs_phocus.py` → `paired/flatfield.py` → `paired/phocus_tone.py`：X2D 配对、扣除位置效应、Phocus 曲线和起点配置文件。
2. `scripts/raw/decode.py`（A6300 RAW）→ `a6300_cells.py`：A6300 格子。白平衡用 `data/raw/patches_raw.json`。
3. `paired/synth.py` → `KMODEL=0.4212 paired/pure_correct.py`：Standard。
4. `paired/nature_pairs.py` → `paired/nature_build.py`（用第 3 步的 Standard）→ `KMODEL=0.4212 paired/pure_correct.py`（起点为 `nature_build.py` 写出的 `start.dcp`）：Nature。
5. 用 `scripts/export_tables.py` 把结果 DCP 里本项目自己的标签（LookTable、色调曲线、曝光偏移、名称）写进 `data/profiles.json` 和 `data/tables/`，`build.sh` 重建后应与拟合出的 DCP 一致。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从带 RGB 曲线的预设切换过来时，曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被 LookTable 推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。

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
