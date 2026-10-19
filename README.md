# A6300 理光 GR III / 富士胶片模拟 / 哈苏 X1D Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并用 dpreview 影棚 RAW 做跨机色彩对齐。
- **A6300 富士模拟**：使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的富士 LUT。A6300 底片在上游版本上加一张颜色表，按 X-S10 + Adobe Camera PROVIA 的 Lightroom 实际输出校准。
- **A6300 哈苏模拟**：Hasselblad X1D 的 Phocus Standard 和 Nature 风格，按 dpreview 同一批拍摄的 A6300 RAW 和 X1D Phocus 输出拟合。

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

## 哈苏 X1D（`scripts/fit/hasselblad/`）

目标是 X1D 的 Phocus 输出（Adobe RGB TIFF），与 A6300 属于同一批拍摄。

1. **初始拟合**（`hbfit.py`、`hbbuild.py`）：A6300 基础颜色 → X1D 输出。用灰阶拟合色调曲线，用色卡拟合 LookTable（核回归）。BaselineExposureOffset +0.338，使 A6300 进入 LookTable 时的亮度对应 K=0.66。
2. **整张图修正**（`align.py`、`warp.py`、`dense_sample.py`、`dense_correct.py`）：
   - 对齐：先做仿射，再按 64px 块做相关匹配，最后拟合三次多项式形变。中位残差约 1.6 px，见 `data/hasselblad/align_check.png`。
   - 取样：约 7 万个平整色块；左半边用于拟合，右半边和两个色轮用于检验。
   - 修正：叠加到 LookTable 上，幅度有上限：色相 ±10°，饱和度 ×0.8–1.2，明度 ×0.93–1.05。
3. **高饱和区淡出**（`satfade.py`）：饱和度高于所有校准样本的区域（HSV s 0.74→0.92），LookTable 的色相和饱和度修正逐渐收回到不处理，不在没有数据的地方外推。
4. **Nature**（`nature_measure.py`、`nature_build.py`）：
   - 测量 Nature 相对 Standard 的差别：Phocus 把白平衡固定在 5500K、色调 +10，造成灰阶整体偏青蓝；此外红、橙、肤色往品红方向转约 10°。
   - 颜色差异叠加到 Standard 的 LookTable 和色调曲线上，高饱和区按 0.74→0.85 淡出。
   - 预设 “Hasselblad X1D Nature” 的白平衡跟随拍摄设置；“Hasselblad X1D Nature 5500K” 另用 RGB 点曲线模拟上述偏色。
5. **暖光**（`lowlight_sample.py`、`warm_matrix.py`）：用 dpreview 低光样张（约 2550K，A6300 RAW 与 X1D Phocus 输出，构图与日光组相同，沿用日光组的对齐）。
   - 只修改 StdA（2856K）端的 ForwardMatrix：FM1′ = C·FM1。C 的 6 个非对角项是自由参数，对角项由"D50 白点不变"确定，所以中性灰保持中性。
   - 目标：色卡和棋盘格训练块的 ΔE2000 最小，曝光按 N5 对齐。肤色色相的块做约束，误差变大就罚分。另加正则 15·|C−I|²。
   - D65 端精确补偿：FM2′ = FM2 + w/(1−w)·(FM1 − FM1′)，w 为日光照片的 StdA 权重（0.04），所以日光下插值后的矩阵完全不变。
   - Standard 和 Nature 共用这组矩阵。

Standard 的检验结果（ΔE2000 均值）：色卡 0.83，右半边彩色 1.77，右半边中性色 1.85，色轮区域的密集取样 1.80，原 48 点色轮 4.76。

暖光（约 2550K）：色卡 4.25，色卡肤色块 2.85，场景肤色检验块 6.44，色轮区域 2.87，灰阶 0.61。

## 预设（`scripts/groups.py`、`templates/hasselblad/`）

DCP 不能指定分组，所以给每个配置文件生成 Look 类型的 XMP（`crs:CameraProfile` 指向 DCP，仅限 ILCE-6300）和对应的预设。富士 22 个 XMP 的组名改为 “A6300 富士模拟”。只选择配置文件的预设都显式写入直线点曲线，所以从 “Nature 5500K” 切换到其他预设时，RGB 曲线会被复位。

## 检查（`scripts/fit/checks/`）

- 合成颜色扫描：检查高饱和区是否被颜色表推出 sRGB。
- 真实照片：在 A6300 照片上统计超出 sRGB 的像素比例。18 张照片的平均值：Adobe Standard 1.02%，理光 0.23–0.40%，富士底片 0.78%，哈苏 Standard 1.92%，Nature 1.72%。

## 局限

- 理光和富士只用影棚日光（约 D65 端点）校准。哈苏另有暖光（约 2550K）一个测量点，中间色温靠 Lightroom 插值。低色温 LED、荧光灯等光谱不连续的光源都没有验证。
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
data/profiles.json, data/tables/  哈苏 Standard/Nature（暖光端 ForwardMatrix、LookTable、色调曲线、曝光偏移）、富士底片的 LookTable
data/hasselblad/          X1D Phocus 色卡/色轮测量、Nature 测量、对齐检查图
templates/                安装说明和哈苏预设
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。`data/tables/` 只包含本项目拟合的部分（LookTable、色调曲线、哈苏暖光端的 ForwardMatrix），其余矩阵和 HueSatMap 在构建时从本机读取。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW、Phocus 和 Lightroom 导出图不在仓库内，`data/` 只保存测量值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
