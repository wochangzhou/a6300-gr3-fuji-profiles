# A6300 理光 GR III / 富士胶片模拟 / 哈苏 X1D Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并用 dpreview 影棚 RAW 做跨机色彩对齐。
- **A6300 富士模拟**：使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的富士 LUT；上游 A6300 底片加一张颜色表，按 X-S10 + Adobe Camera PROVIA 的 Lightroom 实际输出校准（不加曝光偏移）。
- **A6300 哈苏模拟**：Hasselblad X1D 的 Phocus Standard 与 Nature 风格，按 dpreview 同一批拍摄的 A6300 RAW 与 X1D Phocus 输出拟合。

定位：这是一个**基于 Adobe 配置文件的风格移植实验**，不是对理光或富士机内色彩的复刻。仓库只包含生成流程、测量数据和文档；配置文件由 `build.sh` 用你本机的 Lightroom 和上游仓库生成（见“版权说明”）。

## 快速开始

需要 macOS、Lightroom Classic（或用 `LR_PROFILES` 指向 Camera Raw 的 CameraProfiles 目录）、python3、git；构建过程不需要第三方 Python 库（拟合脚本除外）。

```bash
./build.sh            # 输出到 ./build/export
```

两个 zip 包里附有安装说明：把文件复制到 `~/Library/Application Support/Adobe/CameraRaw/` 下的 `CameraProfiles` 和 `Settings`，重启 Lightroom。打开 A6300 的 RAW 后，配置文件浏览器和预设面板里会出现 “A6300 理光模拟”、“A6300 富士模拟”、“A6300 哈苏模拟” 三组。

构建需要 python3；哈苏和富士底片由 `scripts/assemble.py` 把本项目拟合的表（`data/profiles.json`、`data/tables/`）与本机 Lightroom 的 Adobe Standard / 上游底片的矩阵组合生成。`scripts/fit/` 里的拟合脚本另外需要 numpy、rawpy、tifffile，以及不在仓库里的 dpreview RAW 和 Lightroom/Phocus 导出图，构建时不运行。

## 方法

### DCP 管线

```
相机 RGB ─白平衡→ ─ForwardMatrix→ XYZ D50 → ProPhoto 线性
        ─HueSatMap→ “基础颜色” ─LookTable（风格）→ ─曝光偏移 + ToneCurve→ 输出
```

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现了 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出）。验证脚本另外实现了 SDK 的保色相 RGB 色调曲线；生成 DCP 时只原样复制 `ProfileToneCurve`。

### 1. GR III 风格移植（`scripts/port.py`）

以 GR III 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间：对新 LookTable（90×16×16，sRGB 编码）的每个节点，迭代反解对应的 GR III 相机 RGB（不截断负值），用 Adobe 的 GR III 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（+0.55）和 DefaultBlackRender 沿用 GR 原版。建表时节点输入按 DNG 渲染顺序视为已乘曝光的基础颜色（GR 侧：LookTable 作用于 E·(FM·c)）。

### 2. 跨机对齐：在基础颜色层用 RAW 测量

数据：dpreview 影棚场景的三张 RAW（A6300、GR III、X-S20），日光、ISO 200、1/80 s、f/5.6。

1. `scripts/raw/decode.py`（rawpy/LibRaw）：只去马赛克，得到线性相机 RGB（无白平衡、无色彩转换）。
2. `scripts/raw/extract.py`：取 24 色卡每块中心 60×60 像素均值；`scripts/raw/wheel.py`：在色轮 12 个扇区 × 4 圈取 48 个点作**独立验证集**。结果在 `data/raw/`。
3. `scripts/rawbase.py`：用灰块求相机中性点，按 DNG SDK 方式迭代估计色温、插值两组标定（三台机均在 6200～7400 K，基本落在 D65 端点），经 ForwardMatrix → ProPhoto → HueSatMap 得到基础颜色。曝光在 HueSatMap 之前按白块归一化。
4. `scripts/rawfit.py`：A6300 → GR III 的色相差、饱和度比、明度比分别用（色相 × 饱和度）核回归建模，核宽和收缩强度用色卡留一法选，然后在色轮上测试。
5. `scripts/gr3/rawmatch.py`：每个 LookTable 节点先按模型把 A6300 基础颜色转到 GR III 的位置，再查移植后的 GR 风格表。

### 3. 分组（`scripts/groups.py`）

DCP 不能指定组，所以给每个 GR III DCP 生成 Look 类型 XMP（`crs:CameraProfile` 指向 DCP，组 “A6300 理光模拟”，仅 ILCE-6300）及对应预设；富士 22 个 XMP 组名改为 “A6300 富士模拟”（未限制机型）。

## 结果

### 基础颜色层（`rawfit.py`；色相为平均 |Δh|，饱和度/明度为平均 |log 比值|）

| | 色卡：不修正 | 色卡：留一法 | **色轮（独立）：不修正** | **色轮（独立）：修正后** |
|---|---|---|---|---|
| GR III 色相 | 2.17° | 1.64° | 3.82° | **3.07°** |
| GR III 饱和度 | 0.041 | 0.019 | 0.151 | **0.127** |
| GR III 明度 | 0.036 | 0.010 | 0.064 | **0.046** |
| X-S20 色相 | 2.29° | 1.85° | 3.26° | 3.99°（变差） |
| X-S20 饱和度 | 0.038 | 0.038 | 0.095 | 0.096 |

### 端到端（`scripts/gr3/e2e.py`）

色轮 48 点：GR III RAW → Adobe GR III 风格，对比 A6300 RAW → 各版本配置文件。按 DNG SDK 的实际渲染顺序（HueSatMap → 曝光 BaselineExposureOffset +0.55 → LookTable → 色调曲线）计算，ΔE2000 平均（90 分位）：

| 风格 | 仅移植 | **RAW 对齐（当前）** |
|---|---|---|
| Standard | 4.57（7.19） | **4.17**（6.83） |
| Positive Film | 4.83（8.48） | **4.44**（8.23） |
| Negative Film | 3.89（8.96） | **3.55**（7.54） |
| Vivid | 4.75（7.60） | **4.40**（7.81） |

渲染顺序修正：早期版本假设曝光在 LookTable 之后，LookTable 节点按未曝光的基础颜色计算。现在移植（`port.py`）和对齐（`gr3/rawmatch.py`）都按“曝光后的基础颜色”建表，两边按同一场景白归一化后使用相同的曝光量。因为 GR III 的 HueSatMap 是 2.5D（与明度无关），旧表和新表只在最亮一层（接近截断的高光）明显不同（色相最多约 5°、饱和度比约 0.2），中间调差异 <0.1°。所以修正对色轮结果影响很小：用正确顺序评估时旧版 RAW 对齐为 4.18 / 4.45 / 3.55 / 4.40，新版 4.17 / 4.44 / 3.55 / 4.40；表格整体比旧 README 中的数字（4.01 / 4.22 / 3.52 / 4.15，按错误顺序评估）高约 0.1–0.25，这是评估方法的变化，不是配置文件变差。

结论：
- GR III：RAW 对齐在独立样本上平均降低约 10% 色差；早期基于网页截图的对齐在独立样本上反而比不对齐更差，已弃用。
- 富士：早期用 X-S20 RAW 做的基础颜色对齐在色轮上变差，已撤销。现在的颜色表改用 X-S10 的 Lightroom 实际输出校准（见下文）。
- 剩余约 4 ΔE2000 的平均差异主要来自传感器光谱差异和仅 18 个彩色块的约束，不应理解为“已复现 GR III 色彩”。

### 曝光基准

DNG 管线先施加曝光、再查 LookTable，所以两台机进入 GR 风格表时的亮度必须一致。A6300 版沿用 GR 原版的 BaselineExposureOffset +0.55。早期曾按 Lightroom 实测把 A6300 下调 0.38 EV，后来查明这是 dpreview 拍摄批次的差异：2016 年那批（A6300、X1D）本身就更亮（Adobe Standard 下 N5：A6300 47.2%，GR III 40.2%，X-S10 42.2%）。所以不做这项修正。跨机比较曝光时，只比较同一批拍摄的相机。

## 富士底片颜色表（`scripts/fit/fuji/fjfit.py`）

目标是 X-S10（2020，X-Rite ColorChecker，和 A6300 用同一种色卡）在 Lightroom 里套 Adobe "Camera PROVIA/Standard" 的导出；对照是 A6300 + Provia LUT 的导出。在 A6300 底片的基础颜色上，用核回归拟合色相/饱和度残差，写成 90×16×16 的 LookTable。不加曝光偏移：两批拍摄的亮度差（约 0.26 EV）属于批次差异。

在 Lightroom 实际导出上测量（不计亮度的 ΔE2000）：色卡 1.54→0.92，色轮（独立）2.48→1.99。这张颜色表只用 Provia 验证过，但会影响全部 11 种风格。

## 哈苏 X1D（`scripts/fit/hasselblad/`）

数据：dpreview 影棚场景里 A6300 和 X1D 是同一批拍摄（2016），X1D 用 Phocus 输出 Standard / Nature 的 TIFF（Adobe RGB）。

1. `hbfit.py`、`hbbuild.py`：A6300 基础颜色（`rawbase.py`）→ X1D 输出。用灰阶拟合色调曲线，用色卡拟合 LookTable（核回归）。BaselineExposureOffset +0.338 让 A6300 进入 LookTable 时的亮度对应 K=0.66。
2. `hbshift2.py`（去洋红）：拿 Lightroom 真实导出和 Phocus 目标对比，修正彩色节点。色卡 Δa +1.37→+0.03，色轮 Δa +3.21→+1.92。
3. `satfade.py`：饱和度超出所有校准样本的区域（HSV s 0.74→0.92），把 LookTable 的色相和饱和修正逐渐收回为不处理，避免在没有数据的地方外推。镜片镀膜反光这类高饱和蓝紫原本会被推出色域。
4. `align.py`、`warp.py`、`dense_sample.py`、`dense_correct.py`：把整张图对齐（仿射 → 64px 块相关匹配 → 三次多项式形变，中位残差约 1.6 px，见 `data/hasselblad/align_check.png`）。取约 7 万个平整色块；左半边拟合，右半边和两个色轮做检验。在第 3 步的结果上叠加一层修正，修正幅度有上限（色相 ±10°，饱和 ×0.8–1.2，明度 ×0.93–1.05）。
5. `nature_measure.py`、`nature_build.py`：Nature 相对 Standard 的差别。灰阶整体偏青蓝，来自 Phocus 把白平衡固定在 5500K、色调 +10；另有红、橙、肤色往品红方向转约 10°。颜色差异叠加到 Standard 的 LookTable 和色调曲线上，之后用 `satfade.py`（0.74→0.85）淡出高饱和区。偏色本身不放进配置文件，改由预设 "Nature 5500K" 用 RGB 点曲线模拟。

整张图检验（ΔE2000 均值，第 3 步 → 最终）：右半边彩色 2.13→1.72，中性 1.90→1.81；色轮区域的密集取样 1.91→1.75；原 48 点色轮 4.63→4.62。

所有只选配置文件的预设都显式写入直线点曲线，切换预设时会清掉 "Nature 5500K" 的 RGB 曲线。

`scripts/fit/checks/`：高饱和外推检查（合成颜色扫描），以及在真实 A6300 照片上统计超出 sRGB 的像素比例。18 张照片的平均值：Adobe Standard 1.02%，理光 0.23–0.40%，富士底片 0.78%，哈苏 Standard 1.92%、Nature 1.72%。

## 局限

- 只有一种光源（影棚日光，约 D65 端点）。钨丝灯、低色温 LED、荧光灯下的表现没有验证；移植本身也只用了 D65 端点的标定。
- 三台机使用不同镜头（FE 55mm F1.8 / GR 18.3mm / XF56mm F1.2），镜头的色差和眩光会混入测量。
- 三台机是 dpreview 在不同年份分别拍摄的，灯光、色卡实物可能不同。
- 验证集（色轮）仍来自同一张照片和同一光源，只能说明对“别的颜色”能推广，不能说明对“别的光源”能推广。
- Positive Film 等高饱和风格会把阳光下的饱和红推出 sRGB 色域；这是 Adobe 的 GR 风格本身的特性（GR III RAW 上同样出现），本项目不处理。
- Lightroom 的实际渲染没有和模拟器逐像素对照，只验证了 DNG SDK 参考实现。

## 目录

```
build.sh                  一键生成（纯 python3，无第三方库）
scripts/dcp.py            DCP（TIFF/IIRC）读取
scripts/port.py           DNG 查表实现 + GR III 风格移植 + DCP 写出
scripts/rawbase.py        相机 RGB → 各机 Adobe Standard 基础颜色
scripts/rawfit.py         A6300 → GR III 修正拟合 + 色轮独立测试
scripts/gr3/rawmatch.py   生成对齐后的 GR III 配置文件
scripts/gr3/e2e.py        端到端 ΔE2000 检验
scripts/groups.py         分组 XMP（含切换预设时复位点曲线）
scripts/assemble.py       哈苏 / 富士底片：本项目的表 + 本机的 Adobe/上游矩阵 → DCP
scripts/export_tables.py  从拟合好的 DCP 导出本项目自己的标签到 data/
scripts/fit/              拟合与检查脚本（构建时不运行）
scripts/raw/              RAW 解码与取样（需要 rawpy、numpy；坐标对应 dpreview 影棚 RAW）
data/raw/                 色卡与色轮的线性相机 RGB 均值
data/profiles.json, data/tables/  哈苏 Standard/Nature、富士底片的 LookTable、色调曲线、曝光偏移
data/hasselblad/          X1D Phocus 色卡/色轮测量、Nature 测量、对齐检查图
templates/                zip 包里的安装说明
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP；`data/tables/` 只包含本项目拟合的 LookTable 和色调曲线，矩阵与 HueSatMap 在构建时从本机读取。
- dpreview 的 X1D/X-S10 样张和 Phocus 导出图不在仓库内，`data/` 只保存测量值。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW 文件不在仓库内，`data/raw/` 只保存测得的色块均值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
