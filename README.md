# A6300 理光 GR III·GR IV / 富士胶片模拟 / 哈苏 X1D·X2D Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 和 GR IV 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300。
- **A6300 富士模拟**：直接使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的 A6300 底片和富士 LUT（上游原版），只改分组名。
- **A6300 哈苏模拟**：Hasselblad X1D 的 Phocus Standard、Nature 风格，X2D 的 Phocus Standard 和 Nature。用哈苏相机自己的“Adobe Standard → Phocus”同机配对，把差异迁移到 A6300 的 Adobe Standard 上。

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

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出），所以所有 LookTable 都用 90×16×16 的 3D 表。检查脚本另外实现了 SDK 的保色相 RGB 色调曲线。

## 原则：只迁移同一台相机上的“Adobe Standard → 目标风格”差值

dpreview 影棚不同年份、不同机型的拍摄批次，灯光、色卡版本和曝光都不一样（例如 2016 年那批的 A6300 和 X1D 比后来的 GR III、X-S10 那批亮，GR IV 那批换成了 Calibrite 色卡）。拿 A6300 的样张和别的机型的样张直接对齐，学到的差别里会混进批次差异，所以本项目**不做跨机型的样张对齐**。每个风格都只在目标相机自己身上计算“Adobe Standard → 风格”的差值，再接到 A6300 自己的 Adobe Standard 上：

- 理光：差值由 Adobe 的 GR DCP 逐节点精确计算，不用照片。
- 富士：用上游原版。
- 哈苏：Phocus 是黑箱，用同一张哈苏 RAW 的 Adobe Standard 导出和 Phocus 导出配对来学差值。

这样做假设 Adobe Standard 已经把各台相机校准到相近的颜色；两块传感器之间的同色异谱差异不在修正范围内。

## 理光 GR III / GR IV（`scripts/port.py`）

以 GR 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间。对新 LookTable 的每个节点，迭代反解对应的 GR 相机 RGB（不截断负值），用 Adobe 的 GR 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。节点输入是已乘曝光的基础颜色。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（GR III +0.55，GR IV +0.5）和 DefaultBlackRender 沿用 GR 原版。`port.py` 的最后一个参数选机型（`"GR III"` 或 `"GR IV"`），并用 3000 个随机颜色检查移植误差（sRGB 编码下最大约 0.07–0.16，主要在高饱和边缘）。

## 富士底片

上游原版 `Sony ILCE-6300 Adobe Standard Linear.dcp` 和 22 个 LUT XMP，不加颜色表，不加曝光偏移。

## 哈苏 X1D / X2D（`scripts/fit/hasselblad/`）

目标是哈苏的 Phocus 输出（Adobe RGB TIFF）。Phocus 导出时白平衡用吸管点色卡灰块，色卡灰阶的 a*、b* 在 ±0.6 以内。

### 流程：同机配对（`paired/`）

每台哈苏只和自己比：同一个 RAW 在 Lightroom 里用 Adobe Standard 导出（中灰 N5 对齐到 Phocus 输出的 L*，白平衡点 N5），与 Phocus 输出逐像素配对。两边是同一帧、同一张色卡、同一种光，差异只来自“Adobe Standard → Phocus”的渲染。再把这个差异迁移到 A6300 自己的 Adobe Standard 上。A6300 的颜色不和任何哈苏照片直接拟合。

渲染顺序：白平衡 → ForwardMatrix 和 HueSatMap（都是 A6300 的 Adobe Standard 原版）→ BaselineExposureOffset +0.085 → LookTable（90×16×16，同机配对拟合）→ Phocus 色调曲线。

1. **配对**（`pairs.py`）：两张图对齐（残余位移 ≤8 px，按块校正），取约 4–8 万个平整格。Phocus 比 Adobe Standard 更浓（X1D C* +6～+20，X2D +2～+12），高光更亮（L*>70 时约 +4）。曝光必须在导出时就按 N5 对齐，事后补增益的配对效果更差。
2. **中性轴对齐**（`grey_axis_match.py`）：配对里的近中性格（Adobe Standard C*<3）上，Phocus 与 Adobe Standard 还有一点随亮度变化的偏色（X2D 偏暖 Δb 约 +0.3～+1.3，X1D 偏冷 −0.4～−1.4，方向相反，说明主要来自两边白平衡设置）。按 L* 每 5 一段求各通道的对数比，跨亮度平滑（σ 8 L*），只改色度、不改亮度，使灰阶两边一致。之后各亮度段残差在 ±0.4 以内，彩色的 C* 基本不变。Nature 先用 `neutralise.py` 去掉 5500K 固定白平衡的大偏色（偏色由 5500K 预设负责），再做这一步；直接对原始 Nature 配对做会把 C* 压低约 2，不采用。
3. **A6300 取样**（`../align.py`、`../warp.py`、`../dense_sample.py`）：在 A6300 的 dpreview 日光 RAW 上取约 7 万个 6×6 平整格的基础颜色（白平衡 → ForwardMatrix → HueSatMap），两个色轮不参与训练。同一批（2016 年）X1D 的 Phocus 输出对齐到同一网格，只用于对照和验证，不参与拟合。
4. **迁移到 A6300**（`synth.py`）：把配对得到的差异（在 Lab 里按颜色核回归，记为 g）作用到 A6300 自己的 Adobe Standard 导出（N5 同样对齐）上，得到每个格子的合成目标。只保留 g 有数据支撑的格子。
5. **验证**（`validate.py`）：只用 X1D 的配对学 g，完全不用 A6300 数据拟合，再和 X1D 的 Phocus 输出比（6.5 万个格子，ΔE2000）：彩色 4.11 → 2.24（右半边 4.17 → 2.33），中性 1.72 → 1.20，色轮区域 2.24 → 1.17。
6. **颜色表**（`pure_correct.py`）：LookTable 从恒等表开始，直接拟合合成目标（核回归，按 125px 棋盘格分训练/检验，不做高饱和淡出）。幅度上限：色相 ±25°，饱和度 ×0.6–1.6，明度 ×0.85–1.15（实际用到的最大值约 14°、×0.63–1.42、×0.93–1.08）。
7. **曝光**：同一个 RAW，Phocus 比 Lightroom 的 Adobe Standard 暗约 0.2 EV（X1D、X2D 相同），A6300 套用时保持这个关系：BaselineExposureOffset +0.085。
8. **Nature**：X1D Nature 用同样的流程（配对 x1d_nature.tif 与 Adobe Standard 导出，色调曲线用 Phocus Nature 的）。X2D 没有 Phocus Nature 样张，用 `transfer_nature.py` 把 X1D Nature 相对 X1D Standard 的差别（LookTable 每个节点的色相偏移、饱和度和明度比例，以及 Nature 色调曲线）套到 X2D Standard 上，没有经过 X2D 样张验证。

对各自合成目标的检验结果（ΔE2000 均值；“起点”为恒等 LookTable）：

| 配置文件 | 检验彩色 | 中性 | 色轮区域（未训练） |
|---|---|---|---|
| X1D Standard | 1.44 → 0.83 | 1.09 → 1.06 | 1.35 → 1.10 |
| X1D Nature | 1.31 → 0.85 | 1.12 → 1.08 | 1.21 → 1.03 |
| X2D Standard | 1.40 → 0.85 | 1.11 → 1.06 | 1.14 → 1.02 |

注意：中性轴对齐后，X1D 的合成目标离真实 X1D Phocus 反而远了（彩色 1.44 → 2.03，灰阶 b 约 −1）：X1D 配对里那点偏冷可能本来就是 Phocus 的样子。实拍对比后仍选用对齐后的版本。

### 复现步骤

需要：哈苏 RAW 的 Phocus 导出（Adobe RGB 16 位 TIFF）和同一 RAW 的 Lightroom Adobe Standard 导出（ProPhoto 16 位 TIFF，N5 对齐，白平衡点 N5），A6300 的 dpreview 日光 RAW 及其 Adobe Standard 导出，都转成 `.npy`。脚本在 `scripts/fit/hasselblad/`，参数见各文件开头。

1. `paired/pairs.py`：每组（X1D 日光、X1D Nature、X2D 日光）生成配对格。Nature 再跑 `paired/neutralise.py`。
2. `paired/grey_axis_match.py`：日光配对（含 Nature）做中性轴对齐。
3. `align.py` → `warp.py` → `dense_sample.py`：A6300 日光格（`samples6.npz`）。A6300 的白平衡用 `data/raw/patches_raw.json`（由 `scripts/raw/decode.py`、`extract.py` 测得）。
4. `paired/synth.py`：每组配对 + A6300 导出 → 合成目标（`samples6.npz`）。可先跑 `paired/validate.py` 检查迁移。
5. `paired/pure_correct.py`：从当前配置文件（取其矩阵、HueSatMap、色调曲线）出发，恒等 LookTable + 拟合 → 日光 LookTable。Nature 用 Nature 色调曲线的配置文件出发。
6. `paired/transfer_nature.py`：X1D Nature 差别 → X2D Nature。
7. 用 `scripts/export_tables.py` 把结果 DCP 里本项目自己的标签（LookTable、色调曲线、曝光偏移、名称）写进 `data/profiles.json` 和 `data/tables/`，`build.sh` 重建后应与拟合出的 DCP 一致。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从 “Nature 5500K” 切换到其他预设时，RGB 曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被 LookTable 推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。

## 局限

- 只迁移“Adobe Standard → 风格”的差值，不模拟目标相机传感器本身的色彩特性（同色异谱）。Adobe Standard 对两台相机校准得越接近，结果越接近目标相机。
- 哈苏的配对只在 dpreview 影棚日光一个光源下做；X2D Nature 是由 X1D 的 Nature 差别推算的，没有 X2D 样张验证。
- 哈苏的验证集来自同一张照片和同一光源，只能说明对“别的颜色”能推广，不能说明对“别的光源”能推广。
- Positive Film 等高饱和风格会把阳光下的饱和红推出 sRGB 色域，这是 Adobe 的 GR 风格本身的特性。

## 目录

```
build.sh                  一键生成（纯 python3）
scripts/dcp.py            DCP（TIFF/IIRC）读取
scripts/port.py           DNG 查表实现 + GR III / GR IV 风格移植 + DCP 写出
scripts/groups.py         分组 XMP（含点曲线复位）
scripts/assemble.py       哈苏：本项目的表 + 本机的 A6300 Adobe Standard → DCP
scripts/export_tables.py  从拟合好的 DCP 导出本项目自己的标签到 data/
scripts/rawbase.py        相机 RGB → Adobe Standard 基础颜色（哈苏取样用）
scripts/raw/              RAW 解码与 A6300 色卡取样（需要 rawpy、numpy）
scripts/fit/              哈苏拟合与检查脚本（需要 numpy、rawpy、tifffile 和 dpreview 原图；构建时不运行）
data/raw/                 A6300 色卡的线性相机 RGB 均值（哈苏取样的白平衡）
data/profiles.json, data/tables/  哈苏 X1D、X2D 的 Standard/Nature（LookTable、色调曲线、曝光偏移、名称）
data/hasselblad/          同批 X1D Phocus 色卡/色轮测量（只作对照）、A6300↔X1D 取样网格的对齐检查图
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（哈苏的 LookTable、色调曲线），矩阵和 HueSatMap 在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
