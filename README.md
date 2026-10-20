# A6300 理光 GR III / 富士胶片模拟 / 哈苏 X1D·X2D Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并用 dpreview 影棚 RAW 做跨机色彩对齐。
- **A6300 富士模拟**：使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的富士 LUT。A6300 底片在上游版本上加一张颜色表，按 X-S10 + Adobe Camera PROVIA 的 Lightroom 实际输出校准。
- **A6300 哈苏模拟**：Hasselblad X1D 的 Phocus Standard、Nature 风格，X2D 的 Phocus Standard 和 Nature。用哈苏相机自己的“Adobe Standard → Phocus”同机配对（日光和暖光各一组），把差异迁移到 A6300 的 Adobe Standard 上。

定位：这是**基于 Adobe 配置文件的风格移植**，不是对理光、富士或哈苏机内色彩的复刻。仓库只包含生成流程、测量数据、本项目拟合的表和文档；配置文件由 `build.sh` 用你本机的 Lightroom 和上游仓库生成（见“版权说明”）。

## 快速开始

需要 macOS、Lightroom Classic（或用 `LR_PROFILES` 指向 Camera Raw 的 CameraProfiles 目录）、python3、git。构建不需要第三方 Python 库。

```bash
./build.sh            # 输出到 ./build/export
```

生成三个 zip 包，每个包里附有安装说明：把文件复制到 `~/Library/Application Support/Adobe/CameraRaw/` 下的 `CameraProfiles` 和 `Settings`，然后重启 Lightroom。打开 A6300 的 RAW 后，配置文件浏览器和预设面板里会出现 “A6300 理光模拟”、“A6300 富士模拟”、“A6300 哈苏模拟” 三组。

## DCP 渲染顺序

```
相机 RGB ─白平衡→ ─ForwardMatrix→ XYZ D50 → ProPhoto 线性
        ─HueSatMap→ 基础颜色 ─曝光（BaselineExposure + 偏移，截断到 1）→ LookTable（风格）→ ToneCurve → 输出
```

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出），所以所有 LookTable 都用 90×16×16 的 3D 表。检查脚本另外实现了 SDK 的保色相 RGB 色调曲线。

数据：dpreview 影棚场景（日光、ISO 200、1/80 s、f/5.6）。dpreview 不同年份的拍摄批次亮度不同（例如 2016 年那批的 A6300 和 X1D，比后来的 GR III、X-S10 那批亮），所以曝光只在同一批拍摄的相机之间校准。

## 理光 GR III

1. **风格移植**（`scripts/port.py`）：以 GR III 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间。对新 LookTable 的每个节点，迭代反解对应的 GR III 相机 RGB（不截断负值），用 Adobe 的 GR III 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。节点输入是已乘曝光的基础颜色。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（+0.55）和 DefaultBlackRender 沿用 GR 原版。
2. **RAW 测量**：`scripts/raw/decode.py`（rawpy/LibRaw）只做去马赛克，得到线性相机 RGB。`scripts/raw/extract.py` 取 24 色卡每块中心 60×60 像素的均值；`scripts/raw/wheel.py` 在色轮的 12 个扇区 × 4 圈取 48 个点，作为**独立验证集**。结果在 `data/raw/`。
3. **基础颜色**（`scripts/rawbase.py`）：用灰块求相机中性点，按 DNG SDK 的方式迭代估计色温，在两组标定之间插值，再经 ForwardMatrix → ProPhoto → HueSatMap 得到基础颜色。曝光在 HueSatMap 之前按白块归一化。
4. **跨机对齐**（`scripts/rawfit.py`、`scripts/gr3/rawmatch.py`）：A6300 → GR III 的色相差、饱和度比、明度比分别用（色相 × 饱和度）核回归建模，核宽和收缩强度用色卡留一法选择。每个 LookTable 节点先按模型把 A6300 基础颜色转到 GR III 的位置，再查移植后的 GR 风格表。

结果（`scripts/gr3/e2e.py`，色轮 48 点，GR III RAW 经 Adobe GR III 风格 vs A6300 RAW 经本配置文件，ΔE2000 平均 / 90 分位）：Standard 4.17 / 6.83，Positive Film 4.44 / 8.23，Negative Film 3.55 / 7.54，Vivid 4.40 / 7.81。剩余差异主要来自传感器光谱差异，以及只有 18 个彩色块作约束。

## 富士底片（`scripts/fit/fuji/fjfit.py`）

- **目标**：X-S10（X-Rite ColorChecker，与 A6300 用的是同一种色卡）在 Lightroom 里套 Adobe “Camera PROVIA/Standard” 的导出。
- **对照**：A6300 套 Provia LUT 的导出。
- **拟合**：在 A6300 底片的基础颜色上，用核回归拟合色相/饱和度残差，写成 LookTable。不加曝光偏移。

结果（Lightroom 实际导出，不计亮度的 ΔE2000）：色卡 0.92，色轮（独立）1.99。

## 哈苏 X1D / X2D（`scripts/fit/hasselblad/`）

目标是哈苏的 Phocus 输出（Adobe RGB TIFF）。Phocus 导出时白平衡用吸管点色卡灰块，色卡灰阶的 a*、b* 在 ±0.6 以内。

### 流程：同机配对（`paired/`）

每台哈苏只和自己比：同一个 RAW 在 Lightroom 里用 Adobe Standard 导出（中灰 N5 对齐到 Phocus 输出的 L*，白平衡点 N5），与 Phocus 输出逐像素配对。两边是同一帧、同一张色卡、同一种光，差异只来自“Adobe Standard → Phocus”的渲染。再把这个差异迁移到 A6300 自己的 Adobe Standard 上。A6300 的颜色不和任何哈苏照片直接拟合。

渲染顺序：白平衡 → ForwardMatrix（D65 端 = Adobe 原版，StdA 端 = 拟合的 3×3）→ Adobe Standard HueSatMap（StdA 端加红色/肤色色相偏移）→ BaselineExposureOffset +0.085 → LookTable（90×16×16，同机配对拟合）→ Phocus 色调曲线。

1. **配对**（`pairs.py`）：两张图对齐（残余位移 ≤8 px，按块校正），取约 4–8 万个平整格。Phocus 比 Adobe Standard 更浓（X1D C* +6～+20，X2D +2～+12），高光更亮（L*>70 时约 +4）。曝光必须在导出时就按 N5 对齐，事后补增益的配对效果更差。
2. **中性轴对齐**（`grey_axis_match.py`）：配对里的近中性格（Adobe Standard C*<3）上，Phocus 与 Adobe Standard 还有一点随亮度变化的偏色（X2D 偏暖 Δb 约 +0.3～+1.3，X1D 偏冷 −0.4～−1.4，方向相反，说明主要来自两边白平衡设置）。按 L* 每 5 一段求各通道的对数比，跨亮度平滑（σ 8 L*），只改色度、不改亮度，使灰阶两边一致。之后各亮度段残差在 ±0.4 以内，彩色的 C* 基本不变。Nature 先用 `neutralise.py` 去掉 5500K 固定白平衡的大偏色（偏色由 5500K 预设负责），再做这一步；直接对原始 Nature 配对做会把 C* 压低约 2，不采用。
3. **A6300 取样**（`../align.py`、`../warp.py`、`../dense_sample.py`；暖光用 `../lowlight_sample.py`）：在 A6300 的 dpreview 日光 RAW 上取约 7 万个 6×6 平整格的基础颜色（白平衡 → ForwardMatrix → HueSatMap），两个色轮不参与训练。同批 X1D 的 Phocus 输出对齐到同一网格，只用于对照和验证，不参与拟合。
4. **迁移到 A6300**（`synth.py`）：把配对得到的差异（在 Lab 里按颜色核回归，记为 g）作用到 A6300 自己的 Adobe Standard 导出（N5 同样对齐）上，得到每个格子的合成目标。只保留 g 有数据支撑的格子。
5. **验证**（`validate.py`）：只用 X1D 的配对学 g，完全不用 A6300 数据拟合，再和 X1D 的 Phocus 输出比（6.5 万个格子，ΔE2000）：彩色 4.11 → 2.24（右半边 4.17 → 2.33），中性 1.72 → 1.20，色轮区域 2.24 → 1.17。暖光（约 2550K）彩色 5.19 → 3.67。
6. **日光颜色表**（`pure_correct.py`）：LookTable 从恒等表开始，直接拟合合成目标（核回归，按 125px 棋盘格分训练/检验，不做高饱和淡出）。幅度上限：色相 ±25°，饱和度 ×0.6–1.6，明度 ×0.85–1.15（实际用到的最大值约 14°、×0.63–1.42、×0.93–1.08）。
7. **暖光矩阵**（`../warm_matrix.py`）：用低光样张（约 2550K）的合成目标，只修改 StdA（2856K）端的 ForwardMatrix：FM1′ = C·FM1。C 的对角项由“D50 白点不变”确定，中性灰保持中性；肤色做约束，另加正则 2·|C−I|²。D65 端精确补偿 FM2′ = FM2 + w/(1−w)·(FM1 − FM1′)（w 为日光照片的 StdA 权重 0.04），日光下插值后的矩阵完全不变。Nature 与同机型的 Standard 共用。
8. **暖光红色/肤色色相**（`warm_red_hue.py`）：矩阵之后，暖光下红色和肤色仍往品红偏（X1D 红 −8°、肤色 −7°；X2D −5°、−9°），3×3 矩阵无法只修这一段。只在 StdA 端的 HueSatMap 上加一个平滑的色相偏移：HueSatMap 输入色相 348°–8° 全量、两侧各 12° 余弦过渡（336°–20° 以外为零），低饱和处（s<0.12）渐弱到零；只改色相，D65 端同样精确补偿。幅度按数据定：X1D +4.75°，X2D +4.25°。低光色卡其余色块和灰阶不变，日光完全不变。仓库只保存相对 Adobe Standard HueSatMap 的偏移量（`*_hue_offset.bin`），构建时叠加。
9. **曝光**：同一个 RAW，Phocus 比 Lightroom 的 Adobe Standard 暗约 0.2 EV（X1D、X2D 相同），A6300 套用时保持这个关系：BaselineExposureOffset +0.085。
10. **Nature**：X1D Nature 用同样的流程（配对 x1d_nature.tif 与 Adobe Standard 导出，色调曲线用 Phocus Nature 的）。X2D 没有 Phocus Nature 样张，用 `transfer_nature.py` 把 X1D Nature 相对 X1D Standard 的差别（LookTable 每个节点的色相偏移、饱和度和明度比例，以及 Nature 色调曲线）套到 X2D Standard 上，没有经过 X2D 样张验证。

对各自合成目标的检验结果（ΔE2000 均值；“起点”为恒等 LookTable）：

| 配置文件 | 检验彩色 | 中性 | 色轮区域（未训练） |
|---|---|---|---|
| X1D Standard | 1.44 → 0.83 | 1.09 → 1.06 | 1.35 → 1.10 |
| X1D Nature | 1.31 → 0.85 | 1.12 → 1.08 | 1.21 → 1.03 |
| X2D Standard | 1.40 → 0.85 | 1.11 → 1.06 | 1.14 → 1.02 |

暖光（低光合成目标，色卡彩色均值）：X1D 2.72 → 2.53，X2D 2.59 → 2.51；红色色块 X1D 4.69 → 1.46，X2D 3.06 → 1.84。

注意：中性轴对齐后，X1D 的合成目标离真实 X1D Phocus 反而远了（彩色 1.44 → 2.03，灰阶 b 约 −1）：X1D 配对里那点偏冷可能本来就是 Phocus 的样子。实拍对比后仍选用对齐后的版本。

### 复现步骤

需要：哈苏 RAW 的 Phocus 导出（Adobe RGB 16 位 TIFF）和同一 RAW 的 Lightroom Adobe Standard 导出（ProPhoto 16 位 TIFF，N5 对齐，白平衡点 N5），A6300 的 dpreview 日光/低光 RAW 及其 Adobe Standard 导出，都转成 `.npy`。脚本在 `scripts/fit/hasselblad/`，参数见各文件开头。

1. `paired/pairs.py`：每组（X1D 日光、X1D 低光、X1D Nature、X2D 日光、X2D 低光）生成配对格。Nature 再跑 `paired/neutralise.py`。
2. `paired/grey_axis_match.py`：日光配对（含 Nature）做中性轴对齐。
3. `align.py` → `warp.py` → `dense_sample.py`：A6300 日光格（`samples6.npz`）；`lowlight_sample.py`：低光格。
4. `paired/synth.py`：每组配对 + A6300 导出 → 合成目标（日光 `samples6.npz`，低光 `d/samples_low.npz`、`cT_low.npy`）。可先跑 `paired/validate.py` 检查迁移。
5. `paired/pure_correct.py`：从当前配置文件（取其矩阵、HueSatMap、色调曲线）出发，恒等 LookTable + 拟合 → 日光 LookTable。Nature 用 Nature 色调曲线的配置文件出发。
6. `warm_matrix.py`：低光合成目标 → StdA 端 ForwardMatrix（λ=2）。
7. `paired/warm_red_hue.py`：StdA 端 HueSatMap 红色/肤色色相偏移。
8. `paired/transfer_nature.py`：X1D Nature 差别 → X2D Nature。
9. 把结果 DCP 的标签写进 `data/profiles.json` 和 `data/tables/`（HueSatMap 存相对 Adobe 的偏移，`add_to_reference`），`build.sh` 重建后应与拟合出的 DCP 一致。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从 “Nature 5500K” 切换到其他预设时，RGB 曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被颜色表推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。18 张照片的平均值：Adobe Standard 1.02%，理光 0.23–0.40%，富士底片 0.78%，哈苏 Standard 1.92%，Nature 1.72%。

## 局限

- 理光和富士只用影棚日光（约 D65 端点）校准。哈苏另有暖光（约 2550K）一个测量点，中间色温靠 Lightroom 插值。低色温 LED、荧光灯等光谱不连续的光源都没有验证。
- 哈苏的同机配对修正假设 Adobe 给哈苏和 A6300 做的 Adobe Standard 都足够准，同一场景颜色得到相近的输出；两台相机传感器的同色异谱不在修正范围内，暖光下 A6300 的彩色仍偏亮约 3 L*。X2D Nature 是由 X1D 的 Nature 差别推算的，没有 X2D 样张验证。暖光红色/肤色的色相修正只在约 2550K 一个点上拟合。
- 各机型使用不同镜头，镜头的色差和眩光会混入测量。
- 验证集来自同一张照片和同一光源，只能说明对“别的颜色”能推广，不能说明对“别的光源”能推广。
- 富士底片的颜色表只用 Provia 验证过，但会影响全部风格。
- Positive Film 等高饱和风格会把阳光下的饱和红推出 sRGB 色域，这是 Adobe 的 GR 风格本身的特性。

## 目录

```
build.sh                  一键生成（纯 python3）
scripts/dcp.py            DCP（TIFF/IIRC）读取
scripts/port.py           DNG 查表实现 + GR III 风格移植 + DCP 写出
scripts/rawbase.py        相机 RGB → 各机 Adobe Standard 基础颜色
scripts/rawfit.py         A6300 → GR III 修正拟合 + 色轮独立测试
scripts/gr3/rawmatch.py   生成对齐后的 GR III 配置文件
scripts/gr3/e2e.py        端到端 ΔE2000 检验
scripts/groups.py         分组 XMP（含点曲线复位）
scripts/assemble.py       哈苏 / 富士底片：本项目的表 + 本机的 Adobe/上游矩阵 → DCP
scripts/export_tables.py  从拟合好的 DCP 导出本项目自己的标签到 data/
scripts/fit/              拟合与检查脚本（需要 numpy、rawpy、tifffile 和 dpreview 原图；构建时不运行）
scripts/raw/              RAW 解码与取样（需要 rawpy、numpy）
data/raw/                 色卡与色轮的线性相机 RGB 均值
data/profiles.json, data/tables/  哈苏 X1D、X2D 的 Standard/Nature（暖光端 ForwardMatrix、相对 Adobe HueSatMap 的色相偏移、LookTable、色调曲线、曝光偏移）、富士底片的 LookTable
data/hasselblad/          X1D Phocus 色卡/色轮测量（对照用）、A6300↔X1D 取样网格的对齐检查图
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（LookTable、色调曲线、哈苏暖光端的 ForwardMatrix、HueSatMap 的色相偏移量），其余矩阵和 HueSatMap 本身在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
