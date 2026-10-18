# A6300 理光 GR III / 富士胶片模拟 Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成 Lightroom Classic / Camera Raw 配置文件：

- **A6300 理光模拟**：把 Adobe 为 RICOH GR III 做的机内风格模拟（Camera Matching：Standard、Positive Film、Negative Film、Vivid、三种 Monotone）移植到 A6300，并用 dpreview 影棚 RAW 做跨机色彩对齐。
- **A6300 富士模拟**：直接使用 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的富士 LUT 和上游原版 A6300 底片，只做分组。（对齐尝试在独立样本上会变差，见下文。）

定位：这是一个**基于 Adobe 配置文件的风格移植实验**，不是对理光或富士机内色彩的复刻。仓库只包含生成流程、测量数据和文档；配置文件由 `build.sh` 用你本机的 Lightroom 和上游仓库生成（见“版权说明”）。

## 快速开始

需要 macOS、Lightroom Classic（或用 `LR_PROFILES` 指向 Camera Raw 的 CameraProfiles 目录）、python3、git；构建过程不需要第三方 Python 库。

```bash
./build.sh            # 输出到 ./build/export
```

两个 zip 包里附有安装说明：把文件复制到 `~/Library/Application Support/Adobe/CameraRaw/` 下的 `CameraProfiles` 和 `Settings`，重启 Lightroom。打开 A6300 的 RAW 后，配置文件浏览器和预设面板里会出现 “A6300 理光模拟” 和 “A6300 富士模拟” 两组。

## 方法

### DCP 管线

```
相机 RGB ─白平衡→ ─ForwardMatrix→ XYZ D50 → ProPhoto 线性
        ─HueSatMap→ “基础颜色” ─LookTable（风格）→ ─曝光偏移 + ToneCurve→ 输出
```

`scripts/port.py` 按 DNG SDK 参考实现（`dng_reference.cpp` 的 `RefBaselineHueSatMap`）实现了 HSV 查表：三线性插值、色相环绕、sRGB 编码的明度轴，以及单明度层表的特殊路径（不编码输入、仍解码输出）。验证脚本另外实现了 SDK 的保色相 RGB 色调曲线；生成 DCP 时只原样复制 `ProfileToneCurve`。

### 1. GR III 风格移植（`scripts/port.py`）

以 GR III 自己的 Adobe Standard 基础颜色（ForwardMatrix + HueSatMap，D65 端点）为中间空间：对新 LookTable（90×16×16，sRGB 编码）的每个节点，迭代反解对应的 GR III 相机 RGB（不截断负值），用 Adobe 的 GR III 风格渲染，再把结果写成相对节点的色相/饱和度/明度偏移。新表接到 A6300 的矩阵和 HueSatMap 上，色调曲线、曝光偏移（+0.55）和 DefaultBlackRender 沿用 GR 原版。

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

色轮 48 点：GR III RAW → Adobe GR III 风格，对比 A6300 RAW → 各版本配置文件，均含曝光偏移和色调曲线，ΔE2000 平均（90 分位）：

| 风格 | 仅移植 | 旧版截图对齐 | **RAW 对齐（当前）** |
|---|---|---|---|
| Standard | 4.49（6.80） | 4.80（8.19） | **4.01**（6.99） |
| Positive Film | 4.68（7.82） | 5.01（9.32） | **4.22**（8.01） |
| Negative Film | 3.91（8.93） | 4.26（8.50） | **3.52**（7.12） |
| Vivid | 4.63（7.41） | 4.95（8.76） | **4.15**（7.59） |

结论：
- GR III：RAW 对齐在独立样本上平均降低约 10% 色差；早期基于网页截图的对齐在独立样本上反而比不对齐更差，已弃用。
- 富士：无论截图还是 RAW 拟合的对齐，在色轮上都让色相变差，所以不做对齐，使用上游原版底片。可能原因：X-S20 那次拍摄使用了不同的色卡（Calibrite ColorChecker Classic vs X-Rite ColorChecker）和不同年份的布景，以及 X-Trans 的差异。
- 剩余约 4 ΔE2000 的平均差异主要来自传感器光谱差异和仅 18 个彩色块的约束，不应理解为“已复现 GR III 色彩”。

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
scripts/groups.py         分组 XMP
scripts/raw/              RAW 解码与取样（需要 rawpy、numpy；坐标对应 dpreview 影棚 RAW）
data/raw/                 色卡与色轮的线性相机 RGB 均值
templates/                zip 包里的安装说明
```

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），仓库不分发 DCP。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两者均未声明许可证，构建时从上游克隆。
- dpreview 的 RAW 文件不在仓库内，`data/raw/` 只保存测得的色块均值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布。
