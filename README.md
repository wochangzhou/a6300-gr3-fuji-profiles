# A6300 理光 GR III·GR IV / 富士胶片模拟 / 哈苏 X1D·X2D Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 和 GR IV 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并在 Adobe Standard 下按 dpreview 影棚 RAW 色卡做色相/饱和度对齐。
- **A6300 富士模拟**：直接使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的 A6300 底片和富士 LUT（上游原版），只改分组名。
- **A6300 哈苏模拟**：Hasselblad X1D、X2D 的 Standard 和 Nature。Standard 用哈苏相机自己在 Lightroom 里的“Adobe Standard → Camera Standard”同机配对，Nature 用“Adobe Standard → Phocus Nature”配对，把差异迁移到 A6300 的 Adobe Standard 上。

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

dpreview 影棚不同年份、不同机型的拍摄批次，灯光、色卡版本和曝光都不一样（例如 2016 年那批的 A6300 和 X1D 比后来的 GR III、X-S10 那批亮，GR IV 那批换成了 Calibrite 色卡）。所以“Adobe Standard → 风格”的差值只在目标相机自己身上计算，再接到 A6300 自己的 Adobe Standard 上：

- 理光：差值由 Adobe 的 GR DCP 逐节点精确计算，不用照片。
- 富士：用上游原版。
- 哈苏：Standard 用同一张哈苏 RAW 在 Lightroom 里的 Adobe Standard 和 Camera Standard 导出配对；Nature 没有 Lightroom 对应配置文件，用 Phocus Nature 导出配对。

理光另外做一层**跨机色卡对齐**，处理 A6300 和 GR 的 Adobe Standard 对同一张色卡给出的颜色差别。这一层修色相、饱和度和明度。曝光先按白块归一化，所以明度比是按颜色的：GR 的暖色块比 A6300 暗约 5–9%（灰阶一致）。早先不修明度时，A6300 上红、橙、肤色、棕等暖色比 GR 原机亮 GR IV +3～+5 L*、GR III +1.4～+4 L*，实拍看起来红色附近亮了一块；修上后与原机差多在 ±1 L* 以内（按 DNG 参考流程模拟 Adobe 的 GR Camera 风格对比）。修正里同样可能混有批次差异，这是实拍对比后的取舍。

## 理光 GR III / GR IV

1. **风格移植**（`scripts/port.py`）：以 GR 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间。对新 LookTable 的每个节点，迭代反解对应的 GR 相机 RGB（不截断负值），用 Adobe 的 GR 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。节点输入是已乘曝光的基础颜色。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（GR III +0.55，GR IV +0.5）和 DefaultBlackRender 沿用 GR 原版。最后一个参数选机型（`"GR III"` 或 `"GR IV"`）；用 3000 个随机颜色检查移植误差（sRGB 编码下最大约 0.06–0.08，主要在高饱和边缘）。饱和度轴用 32 个节点：GR 的 Adobe Standard 基础颜色到 Camera 风格的映射在饱和度约 0.8 处有一个急拐（橙、橙黄、黄正好在这里），16 个节点时插值会把这些颜色的 C* 压低约 4–8。
2. **RAW 测量**：`scripts/raw/decode.py`（rawpy/LibRaw）只做去马赛克，得到线性相机 RGB。`scripts/raw/extract.py` 取 24 色卡每块中心 60×60 像素的均值；`scripts/raw/wheel.py` 在色轮的 12 个扇区 × 4 圈取 48 个点，作为**独立验证集**。结果在 `data/raw/`（A6300、GR III、GR IV）。
3. **基础颜色**（`scripts/rawbase.py`）：用灰块求相机中性点，按 DNG SDK 的方式迭代估计色温，在两组标定之间插值，再经各自的 Adobe Standard ForwardMatrix → ProPhoto → HueSatMap 得到基础颜色。曝光在 HueSatMap 之前按白块归一化。
4. **跨机对齐**（`scripts/rawfit.py`、`scripts/gr/rawmatch.py`）：A6300 → GR 的色相差、饱和度比分别用（色相 × 饱和度）核回归建模，核宽和收缩强度用色卡留一法选择；近中性色（饱和度 <0.15）逐渐不修。每个 LookTable 节点先按模型把 A6300 基础颜色的色相、饱和度和明度转到 GR 的位置，再查移植后的 GR 风格表。

色卡留一法 / 色轮（独立）结果（`rawfit.py` 输出，色相单位为度，饱和度为对数比）：GR III 色相 2.17 → 1.64 / 3.82 → 3.07，饱和度 0.041 → 0.019 / 0.151 → 0.127；GR IV 色相 3.46 → 2.59 / 4.39 → 3.77，饱和度 0.058 → 0.052 / 0.185 → 0.162。

## 富士底片

上游原版 `Sony ILCE-6300 Adobe Standard Linear.dcp` 和 22 个 LUT XMP，不加颜色表，不加曝光偏移。

## 哈苏 X1D / X2D（`scripts/fit/hasselblad/`）

每台哈苏只和自己比：同一个 RAW 的两份导出逐像素配对，差异只来自渲染（同一帧、同一张色卡、同一种光），再把这个差异迁移到 A6300 自己的 Adobe Standard 上。A6300 的颜色不和任何哈苏照片直接拟合。

- **Standard**：目标是 Lightroom 里哈苏的 **Camera Standard**（Adobe 按 Phocus 渲染做的 Camera Matching 配置文件）。同一个 RAW 在 Lightroom 里导出两次，只换配置文件（Adobe Standard / Camera Standard），白平衡、曝光、镜头校正完全相同，ProPhoto 16 位 TIFF。X1D 的这一对导出曝光 −0.45（高光不溢出），与此前曝光 0 的一对相比，结果在 A6300 上全图只差 ΔE 0.05。
- **Nature**：Lightroom 没有对应的 Camera 配置文件，只能用 Phocus：Phocus Nature 导出（Adobe RGB 16 位 TIFF）与 N5 对齐的 Lightroom Adobe Standard 导出配对。

渲染顺序：白平衡 → ForwardMatrix 和 HueSatMap（都是 A6300 的 Adobe Standard 原版）→ BaselineExposureOffset（Standard 0，Nature +0.11）→ LookTable（90×16×16，同机配对拟合）→ 色调曲线（Standard 为 Adobe Standard 所用的 ACR3 默认曲线，即 DNG SDK 的 `kAdobeDefaultCurve`；Nature 见下）。灰阶在两种配置文件下都与 Adobe Standard 一致。哈苏配置文件不带 DefaultBlackRender（与 Adobe Standard、Camera Standard 一样用默认的 Auto 黑位处理）；设成 None 时中灰会比 Adobe Standard 亮约 1 L*。理光移植版保留 None，与 Adobe 的 GR Camera 配置文件一致。

### Standard（`paired/pairs_lr.py`）

1. **配对**（`pairs_lr.py`）：两份 Lightroom 导出像素对齐，取 4–8 万个平整格。两边白平衡、曝光天然一致：中性格 ΔE 0.4–0.5，各亮度段灰阶 Δa、Δb 在 ±0.4 以内，ΔL* ≤0.3（Camera Standard 与 Adobe Standard 一样亮）；色卡 N5 的 a*、b* 在 ±0.13 以内。Camera Standard 比 Adobe Standard 更浓（X1D C* +3～+14，X2D +1～+10），蓝 180–240° 色相 −6～−10°。
2. **A6300 取样**（`align.py`、`warp.py`、`dense_sample.py`）：在 A6300 的 dpreview 日光 RAW 上取约 7 万个 6×6 平整格的基础颜色（白平衡 → ForwardMatrix → HueSatMap），两个色轮不参与训练。同批（2016 年）X1D 的 Phocus 输出对齐到同一网格，只作对照，不参与拟合。
3. **迁移到 A6300**（`synth.py`，第 8 个参数 `lr`）：A6300 的 Adobe Standard 导出要**关闭镜头校正**，曝光调到中灰与哈苏配对导出一致（N5 L* 约 45，A6300 用 −0.27 EV），白平衡点灰卡（与哈苏导出一致，也与从 RAW 取的基础颜色一致；开着暗角校正时目标在画面边缘比模型亮 +1.3～+1.9 L*）。关闭畸变校正后的取样位置由 `lens_shift.py` 对开着校正的那份导出逐块配准得到（位移 ±3 px，拟合残差 0.2 px），运行时设环境变量 `SHIFT`。把配对差异（在 Lab 里按颜色核回归，记为 g）作用到 A6300 自己的 Adobe Standard 导出上，得到每个格子的合成目标。只保留 g 有数据支撑的格子。
4. **颜色表**（`pure_correct.py`）：起点为 A6300 Adobe Standard 的矩阵和 HueSatMap、ACR3 色调曲线、曝光偏移 0、恒等 LookTable，直接拟合合成目标（核回归，按 125px 棋盘格分训练/检验，不做高饱和淡出）。模型曝光 `KMODEL` 取使 ACR3 曲线给出的 A6300 色卡灰阶与所用 Adobe Standard 导出一致的值（0 EV 导出为 0.5033，−0.27 EV 导出为 0.4212；N8–N3.5 平均差 0.3–0.4 L*）。幅度上限：色相 ±25°，饱和度 ×0.6–1.6，明度 ×0.85–1.15（实际用到的最大值约 15°、×0.84–1.30、×0.96–1.04）。LookTable 在中性色上不改明度。
5. **曝光和色调**：同一个 RAW，Camera Standard 与 Adobe Standard 的灰阶在每一档亮度上都相同（配对 ΔL* ≤0.3），Lightroom 的 Camera Standard 与 Phocus 导出看起来也一样。所以 Standard 直接用 Adobe Standard 的色调曲线和曝光（偏移 0），灰阶与 Adobe Standard 完全相同。早先用 Phocus 拟合的色调曲线在中灰对齐后高光仍偏亮 2–4 L*，已不用。

对各自合成目标的检验结果（ΔE2000 均值；“起点”为恒等 LookTable）：

| 配置文件 | 检验彩色 | 中性 | 色轮区域（未训练） |
|---|---|---|---|
| X1D Standard | 1.09 → 0.93 | 1.00 → 0.98 | 1.14 → 1.07 |
| X2D Standard | 1.08 → 0.96 | 1.13 → 1.10 | 1.15 → 1.10 |

Camera Standard 的合成目标与同批真实 X1D Phocus 输出相比，彩色约 2.1、灰阶 b 约 −0.7（Phocus 略偏冷偏绿），即 Lightroom 的 Camera Standard 与 Phocus 并不完全相同。之前用 Phocus 配对的版本与现在相比，A6300 上全图平均只差 ΔE 0.5–0.6，高饱和色（C*>20）差 2–4；为了数据来源统一，Standard 只用 Lightroom。

### Nature（Phocus 配对，作为相对 Standard 的差别）

Lightroom 没有哈苏 Nature 的 Camera 配置文件，Nature 只能从 Phocus 学，而且只取它**相对 Standard 的差别**，叠到上面 Lightroom 版的 Standard 上。

1. **X1D Nature 差别**（`pairs.py` → `neutralise.py` → `grey_axis_match.py` → `synth.py` → `pure_correct.py`）：Phocus Nature 导出与 N5 对齐的 Lightroom Adobe Standard 导出配对，去掉 5500K 固定白平衡的偏色（由 5500K 预设负责），近中性格按 L* 分段做中性轴对齐，再拟合出 X1D Nature。与同一时期用 Phocus Standard 配对拟合的 X1D Standard（同样的矩阵、HueSatMap 和 Phocus Standard 色调曲线）相比，得到 Nature 相对 Standard 的差别。检验结果：彩色 1.31 → 0.85，中性 1.12 → 1.08，色轮区域 1.21 → 1.03。
2. **叠到 Standard 上**（`transfer_nature.py`，X1D、X2D 都用）：LookTable 每个节点套用这份差别（色相偏移、饱和度和明度比例）。色调差别经 Standard 曲线传递：新曲线 = ACR3(PhocusStandard⁻¹(PhocusNature(x)))。曝光偏移按中灰对齐 Adobe Standard 求得 +0.11，之后色卡六档灰与 Adobe Standard 相差 ≤0.4 L*。X2D 没有 Phocus Nature 样张，用的是 X1D 的差别。

### 复现步骤

需要：哈苏 RAW 在 Lightroom 里的 Adobe Standard 和 Camera Standard 导出（只换配置文件）；X1D Nature 另需 Phocus Nature 导出和 N5 对齐的 Adobe Standard 导出；A6300 的 dpreview 日光 RAW 及其 Adobe Standard 导出（`.npy`）。脚本在 `scripts/fit/hasselblad/`，参数见各文件开头。

1. `align.py` → `warp.py` → `dense_sample.py`：A6300 日光格（`samples6.npz`）。A6300 的白平衡用 `data/raw/patches_raw.json`（由 `scripts/raw/decode.py`、`extract.py` 测得）。
2. Standard：`paired/pairs_lr.py`（X1D、X2D 各一组）→ `paired/synth.py … lr` → `KMODEL=0.5082 paired/pure_correct.py`（起点配置文件换成 ACR3 曲线、曝光偏移 0）。
3. Nature：`paired/pairs.py` → `paired/neutralise.py` → `paired/grey_axis_match.py` → `paired/synth.py` → `paired/pure_correct.py`（Phocus Standard 曲线的配置文件出发）得到 X1D Nature 与对应的 X1D Standard；再 `paired/transfer_nature.py` 把差别叠到 Lightroom 版的 X1D、X2D Standard 上。
4. 用 `scripts/export_tables.py` 把结果 DCP 里本项目自己的标签（LookTable、色调曲线、曝光偏移、名称）写进 `data/profiles.json` 和 `data/tables/`，`build.sh` 重建后应与拟合出的 DCP 一致。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从 “Nature 5500K” 切换到其他预设时，RGB 曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被 LookTable 推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。

## 局限

- 风格差值不包含目标相机传感器本身的色彩特性（同色异谱）。理光的色卡对齐只用 18 个彩色块，而且两台相机的样张来自不同批次，修正里会混有批次差异。
- 哈苏的配对只在 dpreview 影棚日光一个光源下做；X2D Nature 是由 X1D 的 Nature 差别推算的，没有 X2D 样张验证，Nature 的差别本身来自 Phocus，Standard 来自 Lightroom 的 Camera Standard，两者来源不同。
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
data/profiles.json, data/tables/  哈苏 X1D、X2D 的 Standard/Nature（LookTable、色调曲线、曝光偏移、名称）
data/hasselblad/          同批 X1D Phocus 色卡/色轮测量（只作对照）、A6300↔X1D 取样网格的对齐检查图
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（哈苏的 LookTable、色调曲线；Standard 的色调曲线就是 DNG SDK 公开的 ACR3 默认曲线），矩阵和 HueSatMap 在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
