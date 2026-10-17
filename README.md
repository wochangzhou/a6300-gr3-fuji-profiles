# A6300 理光 GR III / 富士胶片模拟 Lightroom 配置文件

为 **Sony A6300（ILCE-6300）** 生成两套 Lightroom Classic / Camera Raw 配置文件，并按 dpreview 影棚场景的 24 色卡做跨机型色彩对齐：

- **A6300 理光模拟**：把 Lightroom 自带的 RICOH GR III 机内风格（Standard、Positive Film、Negative Film、Vivid、Monotone、Soft Monotone、Hard Monotone）移植到 A6300。
- **A6300 富士模拟**：基于 [TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation](https://github.com/TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation) 的富士胶片 LUT，把 A6300 的 Adobe Standard Linear 底片对齐到 Fujifilm X-S20。

本仓库**只包含生成流程、测量数据和文档**，不包含配置文件本身。配置文件需要你在本机运行 `build.sh`，从自己安装的 Lightroom 和上游仓库生成（原因见文末“版权说明”）。

## 快速开始

需要：macOS、Lightroom Classic（或改 `LR_PROFILES` 指向 Camera Raw 的 CameraProfiles 目录）、python3、git。不需要任何第三方 Python 库。

```bash
./build.sh            # 输出到 ./build/export
```

输出两个 zip 包，里面附有安装说明。安装就是把文件复制进 `~/Library/Application Support/Adobe/CameraRaw/` 下的 `CameraProfiles` 和 `Settings`，然后重启 Lightroom。打开 A6300 的 RAW 后，在配置文件浏览器和预设面板里会看到 “A6300 理光模拟” 和 “A6300 富士模拟” 两个组。

## 原理

### DCP 渲染管线

Lightroom 处理 RAW 时，DCP 配置文件按下面的顺序起作用：

```
相机 RGB ─(ForwardMatrix)→ XYZ D50 → ProPhoto 线性
        ─(HueSatMap：按相机校正色相/饱和度/明度)→ “基础颜色”
        ─(LookTable：风格)→ ─(ToneCurve：影调)→ 输出
```

Adobe Standard 的目标是让不同相机的“基础颜色”尽量一致，风格（LookTable 和 ToneCurve）建立在这一层之上。脚本里按 DNG SDK 的参考实现重写了 HSV 查表（三线性插值、色相环绕、sRGB 编码的明度轴）和保色相的 RGB 色调曲线，见 `scripts/port.py`。

### 1. GR III 风格移植（`scripts/port.py`）

GR III 的机内风格 DCP 只能用于 GR III。移植步骤：

1. 以 GR III 自己的 Adobe Standard（ForwardMatrix 加 HueSatMap，不含 LookTable）作为“基础颜色”空间。
2. 对新 LookTable（90×16×16，sRGB 编码）的每个网格点，用迭代法反解出对应的 GR III 相机 RGB。高饱和颜色反解出来可能带负值，**不截断**。
3. 用 GR III 原版风格（自己的 ForwardMatrix、LookTable）渲染这个相机 RGB，再把结果换算成相对网格点的色相、饱和度、明度偏移。
4. 把新 LookTable 接到 A6300 的矩阵和 HueSatMap 上，色调曲线、BaselineExposureOffset（+0.55）和 DefaultBlackRender 都沿用 GR 原版。

这一步的前提是：两台相机的 Adobe Standard 会把同一个场景颜色放到同一个位置。**实测证明这个前提不完全成立**，所以有了第 2 步。

### 2. 跨机型色彩对齐（`scripts/gr3/`、`scripts/fuji/`）

数据来自 dpreview 影棚场景对比工具：两台相机、RAW、同一 ISO，在同一画面里截取 24 色卡。`sample.py` 取每个色块中间 70% 区域的平均值，标准差都在 2 以内；灰阶两边一致，说明白平衡和曝光对得上。测量结果在 `data/` 目录里。

色相差在 ProPhoto 线性 HSV 空间里计算，因为 LookTable 就是在这个空间工作的。在 sRGB 空间测会夸大红色这一段的差异：同一块红色在 sRGB 里差 4.2°，在 ProPhoto 里只差 2.5°。

**A6300 vs GR III**（`scripts/gr3/build3.py`）
- 红、肤色、棕、橙、黄 7 个色块全部是 A6300 偏洋红（ProPhoto +1～5°），方向一致；其他色相没有一致规律。
- 在肤色到棕的色相段（15～35°），偏差和饱和度单调相关：肤色 s=0.41 偏 +5.1°，棕 s=0.56 偏 +3.1°，橙 s=0.84 偏 +1.1°。所以这一段按饱和度插值修正，其余暖色按色相核回归修正，暖色以外的色相不修。
- A6300 的彩色普遍亮约 5.5%（18 个色块同向，灰阶一致），按饱和度加权压暗。
- 修正量是“先把 A6300 的颜色转到 GR III 的位置，再查 GR 风格表”，最后合成进 LookTable。

**A6300 vs X-S20**（`scripts/fuji/fit2d.py`、`buildfuji.py`）
- 差异整体比 GR III 小，红、橙、黄都在 1.5° 以内。
- 修正参数（色相核宽、饱和度核宽、收缩强度）用网格搜索加留一法选出：色相 2.16° → 1.89°，饱和度没有改善（不修），明度 0.020 → 0.013（修）。
- 肤色 +4.6°、绿 -7.8°、青绿 -5.1°、蓝花 +4.8° 都是孤立点，留一法预测不出来，所以不硬修。
- 修正作为一张 90×16×1 的 LookTable 加到 A6300 的 “Adobe Standard Linear” 底片上，名字不变，富士 LUT 照常引用它。

### 3. 分组（`scripts/fuji/groups.py`）

DCP 不能指定组。所以给每个 GR III 的 DCP 生成一个 Look 类型的 XMP 配置文件（`crs:CameraProfile` 指向 DCP，`crs:Group` 设为 “A6300 理光模拟”，只对 ILCE-6300 显示），并配上对应预设；富士的 22 个 XMP 组名改为 “A6300 富士模拟”。

## 验证结果

| 项目 | 结果 |
|---|---|
| 移植正确性（GR III 自身颜色回环） | 绝大多数网格点误差 ≤0.1（sRGB 编码值），极端高饱和色最大约 0.2 |
| GR III 暖色对齐（留一法） | 2.22° → 1.11° |
| GR III 全色卡平均色相误差 | Standard 1.79° → 1.27°，Vivid 1.68° → 1.26° |
| 富士底片对齐（样本内） | 色相 2.16° → 1.16°，明度误差减半；样本外预期约 1.9° |
| 可复现性 | `build.sh` 重新生成的 8 个 DCP 与作者本机安装的版本逐字节一致 |

## 局限

- 测量数据来自 dpreview 网页截图：经过网页压缩，两台相机用的镜头不同，A6300 的蓝和青已经超出 sRGB 色域被截断。剩下的 1～2° 误差基本到了这些数据的精度极限。
- 截图里的颜色已经过 Adobe Standard 的 LookTable 和色调曲线，而修正是加在这之前的基础层上的，属于近似。
- 低饱和暖色（比肤色更淡）的修正是外推的，没有数据点。
- 不确定上游富士 LUT 基于哪台富士机身；对齐目标选了 X-S20。
- 没有用原始 RAW 做逐像素验证，最终效果请以实拍为准。

## 目录

```
build.sh                 一键生成
scripts/dcp.py           DCP（TIFF/IIRC）解析
scripts/port.py          DNG 查表/色调实现 + GR III 风格移植 + DCP 写出
scripts/gr3/             A6300→GR III：取色、拟合、生成
scripts/fuji/            A6300→X-S20：取色、2D 拟合、生成底片、分组 XMP
data/                    色卡测量值（sRGB 8bit，[对比机, A6300]）
templates/               zip 包里的安装说明
```

`sample.py` 里的色块坐标对应作者当时的截图（1916×976），截图本身不在仓库里，换截图需要改坐标。

## 版权说明

- 生成的 DCP 由 Adobe 随 Lightroom 附带的配置文件计算而来（Adobe 版权），所以仓库不分发 DCP，只分发生成方法。
- 富士 LUT 来自 TingfengLuo/Camera-Profile-for-Fujifilm-Film-Simulation 和 abpy/FujifilmCameraProfiles，两个项目都没有声明许可证，仓库不分发，构建时从上游克隆。
- 色卡截图版权属于 dpreview，仓库只保存测出来的数值。
- 本仓库的脚本、数据和文档以 MIT 许可证发布（见 LICENSE）。
