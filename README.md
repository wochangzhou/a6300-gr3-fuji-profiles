# A6300 理光 GR III·GR IV / 富士胶片模拟 / 哈苏 Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 和 GR IV 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并在 Adobe Standard 下按 dpreview 影棚 RAW 做跨机对齐（以色卡为准，场景其余颜色补充）。
- **A6300 富士模拟**：直接使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的 A6300 底片和富士 LUT（上游原版），只改分组名。
- **A6300 哈苏模拟**：Hasselblad Standard 和 Nature，以哈苏 X2D 为准。Standard 用 X2D 在 Lightroom 里的“Adobe Standard → Camera Matching（Camera Standard）”同机配对，Nature 用 X2D 的“Phocus Standard → Phocus Nature”同机配对，叠到 Standard 上。

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

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出），所以所有 LookTable 都用 3D 表（理光 90×32×16，哈苏 90×32×32）。检查脚本另外实现了 SDK 的保色相 RGB 色调曲线。

## 原则：风格差值只在同一台相机上计算

dpreview 影棚不同年份、不同机型的拍摄批次，灯光、色卡版本和曝光都不一样（例如 2016 年那批的 A6300 比后来的 GR III、X-S10 那批亮，GR IV 那批换成了 Calibrite 色卡）。所以“Adobe Standard → 风格”的差值只在目标相机自己身上计算，再接到 A6300 自己的 Adobe Standard 上：

- 理光：差值由 Adobe 的 GR DCP 逐节点精确计算，不用照片。
- 富士：用上游原版。
- 哈苏：Standard 用同一张 X2D RAW 在 Lightroom 里的 Adobe Standard 导出和 Camera Matching 导出配对；Nature 用同一张 X2D RAW 的 Phocus Standard 和 Phocus Nature 导出配对。

理光另外做一层**跨机对齐**，处理 A6300 和 GR 的 Adobe Standard 对同一场景给出的颜色差别，修色相、饱和度和明度。以 24 色卡为准（色卡在画面中央、照明最可靠），dpreview 场景里的其他平整颜色（颜料、色轮、布料、印刷品等，约 3.7 万格）补充色卡覆盖不到的颜色。两台相机的样张来自不同批次，修正里可能混有批次差异，这是实拍对比后的取舍。

## 理光 GR III / GR IV

1. **风格移植**（`scripts/port.py`）：以 GR 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间。对新 LookTable 的每个节点，迭代反解对应的 GR 相机 RGB（不截断负值），用 Adobe 的 GR 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。节点输入是已乘曝光的基础颜色。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（GR III +0.55，GR IV +0.5）和 DefaultBlackRender 沿用 GR 原版。最后一个参数选机型（`"GR III"` 或 `"GR IV"`）；用 3000 个随机颜色检查移植误差（sRGB 编码下最大约 0.06–0.08，主要在高饱和边缘）。饱和度轴用 32 个节点：GR 的 Adobe Standard 基础颜色到 Camera 风格的映射在饱和度约 0.8 处有一个急拐（橙、橙黄、黄正好在这里），16 个节点时插值会把这些颜色的 C* 压低约 4–8。
2. **RAW 测量**：`scripts/raw/decode.py`（rawpy/LibRaw）只做去马赛克，得到线性相机 RGB。`scripts/raw/extract.py` 取 24 色卡每块中心 60×60 像素的均值，结果在 `data/raw/patches_raw.json`（A6300、GR III、GR IV）。
3. **基础颜色**（`scripts/rawbase.py`）：用灰块求相机中性点，按 DNG SDK 的方式迭代估计色温，在两组标定之间插值，再经各自的 Adobe Standard ForwardMatrix → ProPhoto → HueSatMap 得到基础颜色。曝光在 HueSatMap 之前按白块归一化。
4. **场景配对**（`scripts/fit/gr/dense_pairs.py`）：A6300 与 GR 的同一 dpreview 场景 RAW。用已知点（色卡四角、色轮中心、四张人像）求仿射，再逐块精配准并拟合三次多项式变形（残差 GR III 0.8 px、GR IV 2.4 px），在 A6300 的 /4 网格上取 4×4 平整格，约 3.7 万对。GR 的 28mm 镜头四角暗（边缘约为中心的一半），这是位置相关的特性，DCP 无法表达，若不扣除会被误学成“颜色变暗”：在中性格上把 GR/A6300 的比值拟合成位置的二维多项式（三个通道几乎相同），以色卡处为 1，从 GR 一侧扣除。想要 GR 那样的四角压暗，可在预设里另加暗角。
5. **对齐模型**（`scripts/fit/gr/fitcv.py`、`fit_anchor.py`）：A6300 → GR 的色相差、饱和度对数比、明度对数比，按（色相 × 饱和度）分箱取中位数，再用核回归平滑（按样本数加权）。核宽用左右半幅交叉验证选定，并设下限（色相 10°、饱和度 0.1）保证平滑。色卡 18 个彩色块作锚点，每块权重 60，优先对准色卡。结果存为 `data/gr/model_*.json`。
6. **生成**（`scripts/gr/rawmatch.py`）：每个 LookTable 节点先按模型把 A6300 基础颜色的色相、饱和度和明度转到 GR 的位置（饱和度 0.15 以下逐渐不修），再查移植后的 GR 风格表。彩色风格之后沿饱和度方向做单调化（`scripts/fit/hasselblad/paired/monotone.py`，只上调回落处的饱和度倍数），被上调的条目由 `scripts/fit/gr/monotone_export.py` 存为 `data/gr/monotone_*.json`，构建时直接套用，所以 `build.sh` 不需要 numpy。

检验（色相单位为度，饱和度、明度为对数比；括号内为此前只用 18 个色块拟合的模型）：色轮（不参与训练）色相 GR IV 5.51（7.00）、GR III 4.55（4.79），明度 0.034（0.043）、0.030（0.032）；场景另一半色相 4.77（7.07）、6.00（8.71）。按 DNG 参考流程模拟 GR 原机 RAW 套 Adobe 的 GR Camera 风格（`scripts/fit/gr/chart_eval.py`），色卡 18 色平均 ΔE00：GR IV Standard 0.74（1.61），Positive Film 0.73（1.68）；GR III Standard 0.52（0.81），Positive Film 0.61（0.81）。GR IV 的棕、肤色明度差在 +0.7 L* 以内；橙色饱和度差 GR IV −2.7（−8.4）、GR III −3.5（−8.8）。压力测试（`stress.py`）：饱和度反转 ≤0.02%，较大的回落只剩深蓝极端角（输入饱和度 ≥0.94，输出 L* <10、C* >120，超出任何显示色域）。

## 富士底片

上游原版 `Sony ILCE-6300 Adobe Standard Linear.dcp` 和 22 个 LUT XMP，不加颜色表，不加曝光偏移。

## 哈苏（`scripts/fit/hasselblad/paired/`）

以哈苏 X2D 为准，只在哈苏自己身上学差异：同一张 X2D RAW 的两份导出逐像素配对，差异只来自渲染（同一帧、同一张色卡、同一种光）。Standard 的数据全部来自 Lightroom（Adobe Standard 和 Adobe 为 X2D 做的 Camera Matching 配置文件 Camera Standard）；只有 Nature 用到 Phocus，而且只取 Phocus 内部 Standard → Nature 的差别。A6300 的颜色不和任何哈苏照片直接拟合，也不用 A6300 的照片取样：颜色表的每个节点都由 DCP 的计算直接构造。

渲染顺序：白平衡 → ForwardMatrix 和 HueSatMap（都是 A6300 的 Adobe Standard 原版）→ BaselineExposureOffset 0 → LookTable（90×32×32）→ 色调曲线（Standard 为 Camera Matching 灰阶曲线，Nature 在其上叠加 Phocus Nature 的反差）。不带 DefaultBlackRender，与 Adobe Standard 一样用默认的 Auto 黑位处理。理光移植版保留 None，与 Adobe 的 GR Camera 配置文件一致。

### 导出要求

同一张 X2D RAW：Lightroom 分别用 Adobe Standard 和 Camera Standard（Camera Matching）导出（ProPhoto 16 位 TIFF，其他设置相同）；Phocus 导出 Standard 和 Nature（Adobe RGB 16 位 TIFF，设置相同）。白平衡都点色卡灰块，镜头校正都关闭。

### Standard（X2D Lightroom Adobe Standard → Camera Matching）

1. **配对**（`cm_pairs.py`）：两份 Lightroom 导出像素对齐，取约 8 万个 6×6 平整格。中性格白平衡一致（Δa 0～+0.6，Δb −0.15～−0.4），彩色格 Camera Matching 平均 C* +2.4。
2. **色调曲线**（`cm_tone.py`）：中性格（Adobe Standard C*<3）上 Adobe Standard → Camera Matching 的 ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = ACR3 默认曲线（Adobe Standard 用的曲线，DNG SDK `kAdobeDefaultCurve`）输出的 L* 加上这个差值。两者灰阶几乎相同（|ΔL*| ≤ 0.23）。写出起点配置文件（A6300 Adobe Standard 的矩阵和 HueSatMap、这条曲线、曝光偏移 0）。
3. **差异模型 g**（`analytic.py` 内）：Adobe Standard Lab → Camera Matching Lab 的核回归（Lab 分箱取中位差，高斯核加权）。参数用左右半幅交叉验证选定（dpreview 场景左右两边是对称摆放的不同物体，比随机切分更能反映对新物体的推广）：σ = (4, 10, 10)、收缩 λ = 0.02，数据支撑不足处按支撑量渐弱到 0。
4. **逐节点构造**（`analytic.py`）：对颜色表的每个节点 X（已乘曝光的基础颜色），按 DNG 参考流程算出 A6300 的 Adobe Standard 会把它渲染成什么（Adobe Standard 自己的 LookTable + ACR3 曲线），套上 g 得到目标，再按本配置文件的色调曲线（保色相 RGB 曲线）反解出节点应取的值。不依赖场景取样，整个颜色空间都有定义。稳定化：最亮两层沿用下一层（曲线在白附近太平，反解病态）；幅度上限色相 ±25°、饱和度 ×0.6–1.6、明度 ×0.85–1.15；中性轴不改（灰阶只由曲线决定）；饱和度 0.12 以下渐弱到不改。
5. **单调化**（`monotone.py`）：沿饱和度方向逐个节点（每个区间再检查 3 个中间点），保证渲染出的 C* 不回落；只上调出问题节点的饱和度倍数（约 0.5% 的节点，最多 ×1.07）。

### Nature（X2D Phocus Standard → Nature，作为相对 Standard 的差别）

1. **配对**（`nature_pairs.py`）：同一张 X2D RAW 的 Phocus Standard 与 Phocus Nature 导出（同一软件、同尺寸，像素对齐），取约 6 万个平整格。两份的白平衡一致，没有随画面位置的变化。Nature 的反差更大（中性格 ΔL*：暗部 −6，L* 40–60 −2.2，L* 60–80 +2.3，高光 +3.3），彩色更浓。
2. **色调曲线**（`nature_tone.py`）：中性格的 Nature−Standard ΔL*（按 L* 每 2.5 一段、平滑、两端收敛到 0），新曲线 = Standard 曲线输出的 L* 加上这个差值，保持单调（Standard L* 10/30/50/70/90 → −5.2/−5.0/−1.2/+2.8/+3.4）。
3. **颜色表**：同 Standard 的第 3–5 步，源渲染换成上面做好的 Standard（它自己的 LookTable 和曲线），g 为 Phocus Standard Lab → Phocus Nature Lab。这个差别是在 Phocus Standard 的颜色上学到的，套在 Camera Matching 的颜色上，两者接近但不完全相同。曝光偏移 0。

### 压力测试（`stress.py`）

合成网格：色相 1° × 饱和度 0.02 × 24 档亮度，与 Adobe Standard 对照。

- Standard：无饱和度、亮度、色相反转（饱和度最大回落 0.6 C*）；超出配对数据的高饱和区（s≥0.85）偏离 Adobe Standard 平均 1.05、最大 12.3。
- Nature：饱和度反转 0.05%（最大回落 3.6 C*，集中在接近黑色的深暗部和 s≥0.94），亮度反转 0.00%（最大 0.06），无色相反转；s≥0.85 偏离平均 1.9、最大 19.0。

### 复现步骤

需要：上面四份 X2D 导出（16 位 TIFF），ACR3 默认曲线（DNG SDK `kAdobeDefaultCurve`，1025 点文本），本机 Lightroom 的 `Sony ILCE-6300 Adobe Standard.dcp`。参数见各文件开头。

1. Standard：`cm_pairs.py` → `cm_tone.py` → `analytic.py`（`lr lr`，源为 `as:<Adobe Standard.dcp>:<acr3>`，90 32 32）→ `monotone.py`。
2. Nature：`nature_pairs.py` → `nature_tone.py`（用第 1 步的 Standard）→ `analytic.py`（`phocus phocus`，源为第 1 步的 Standard）→ `monotone.py`。
3. 用 `scripts/export_tables.py` 把结果 DCP 里本项目自己的标签（LookTable、色调曲线、曝光偏移、名称）写进 `data/profiles.json` 和 `data/tables/`，`build.sh` 重建后应与拟合出的 DCP 一致。
4. 检查：`stress.py`。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从带 RGB 曲线的预设切换过来时，曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被 LookTable 推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。
- `scripts/fit/hasselblad/paired/stress.py`（哈苏、理光通用）：饱和度、亮度、色相单调性，平滑度，sRGB 外溢，数据之外的偏离。
- 理光：`scripts/fit/gr/chart_eval.py`，色卡与 GR 原机（Adobe GR Camera 风格）的差。

## 局限

- 风格差值不包含目标相机传感器本身的色彩特性（同色异谱）。理光的对齐来自不同批次的样张，修正里会混有批次差异；印刷人像等材料的同色异谱无法完全对齐。
- 哈苏的配对只在 dpreview 影棚日光一个光源下做，只用 X2D 一台相机。
- 哈苏的检验集来自同一张照片和同一光源，只能说明对“别的颜色”能推广，不能说明对“别的光源”能推广。
- Positive Film 等高饱和风格会把阳光下的饱和红推出 sRGB 色域，这是 Adobe 的 GR 风格本身的特性。

## 目录

```
build.sh                  一键生成（纯 python3）
scripts/dcp.py            DCP（TIFF/IIRC）读取
scripts/port.py           DNG 查表实现 + GR III / GR IV 风格移植 + DCP 写出
scripts/gr/rawmatch.py    生成对齐后的 GR III / GR IV 配置文件
scripts/groups.py         分组 XMP（含点曲线复位）
scripts/assemble.py       哈苏：本项目的表 + 本机的 A6300 Adobe Standard → DCP
scripts/export_tables.py  从拟合好的 DCP 导出本项目自己的标签到 data/
scripts/rawbase.py        相机 RGB → 各机 Adobe Standard 基础颜色
scripts/raw/              RAW 解码与色卡取样（需要 rawpy、numpy）
scripts/fit/              哈苏、理光的拟合与检查脚本（需要 numpy、rawpy、tifffile 和 dpreview 原图；构建时不运行）
data/raw/                 A6300、GR III、GR IV 色卡的线性相机 RGB 均值
data/gr/                  理光对齐模型和单调化修正（本项目拟合）
data/profiles.json, data/tables/  哈苏 Standard/Nature（LookTable、色调曲线、曝光偏移、名称）
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（哈苏的 LookTable、色调曲线），矩阵和 HueSatMap 在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
