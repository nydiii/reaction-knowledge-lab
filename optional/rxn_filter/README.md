# 选做：用 RXN Filter 检查反应结构的合理性

本实验不需要 API 或显卡。它接收前面已经解析好的反应物、产物结构，给出一个辅助筛查分数；**不检查产率、温度、时间或来源，也不自动修改知识库**。

论文：*A virtual platform for automated hybrid organic-enzymatic synthesis planning*，**Nature Communications 16, 10929 (2025)**，[DOI](https://doi.org/10.1038/s41467-025-65898-3)。只复现其中 Morgan 指纹版 RXN Filter 的预训练推理，不重训模型、不复现完整合成规划平台的性能指标。

## 1. 本实验沿用了什么

- [作者代码](https://github.com/wangxr0526/ChemEnzyRetroPlanner/tree/7dbab354189db9edc7aea9c0aedc2f1b1659f906/retro_planner/packages/rxn_filter/rxn_filter)：原 `FilterModel` 双分支网络、半径 2 / 2048 位 / 保留手性的 Morgan 指纹、产物指纹减去各反应物指纹之和。
- [作者模型](https://huggingface.co/xiaoruiwang/ChemEnzyRetroPlanner_metadata/tree/main)：2025 年部署权重 `filter_model_20250604_232451_state.pt`，不是旧示例脚本中的 DRFP 模型。
- 课程改造：去掉训练、DRFP、RXNFP 等无关依赖；增加输入检查、CPU 加载、文件哈希核对和命令行输出。`torch.load` 使用 `weights_only=True`。
- 网络结构、权重、指纹含义均未重新训练或替换。原 MIT 许可保存在 [LICENSE](LICENSE)，具体来源及验证记录在 [provenance.json](provenance.json)。

## 2. 单独建立 CPU 环境

在**仓库根目录**打开终端。建议选做实验使用单独环境，避免改变必做实验的依赖。以下命令以 Python 3.12 为准。

macOS：

```bash
python3.12 -m venv .venv-rxn-filter
source .venv-rxn-filter/bin/activate
python -m pip install --upgrade pip
python -m pip install -r optional/rxn_filter/requirements.txt
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv-rxn-filter
.\.venv-rxn-filter\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r optional/rxn_filter/requirements.txt
```

若 PowerShell 阻止激活，可以直接把下文 `python` 换为 `.\.venv-rxn-filter\Scripts\python.exe`，不必修改全局执行策略。Linux 用户也可先用 PyTorch 的 CPU 索引安装 `torch==2.8.0`，再安装 requirements；不要为此安装 CUDA。

验证：

```bash
python -c "import torch; from rdkit import rdBase; print(torch.__version__, rdBase.rdkitVersion)"
```

应看到 torch `2.8.0`（CPU 轮子可能显示 `2.8.0+cpu`）和 RDKit `2025.03.6`。本仓库记录了 macOS Apple Silicon 的实际 CPU 验证；Windows/Linux 的安装命令未在本轮实机验证。

## 3. 下载并核对模型

```bash
python optional/rxn_filter/download_model.py
```

程序只下载约 **31.1 MB** 的独立模型包，并从中提取约 **16.8 MB** 的指定权重，不下载整个 14 GB 平台。预期输出含 `Saved verified CPU-compatible state dictionary`，权重位置为 `optional/rxn_filter/models/rxn_filter_2025.pt`。

如果官方 Hugging Face 站点不可达，可明确选择镜像；镜像文件仍需通过同一组 SHA256 校验：

```bash
python optional/rxn_filter/download_model.py --mirror
```

也可从作者模型页面手动下载 `rxn_filter_metadata.zip`，再运行：

```bash
python optional/rxn_filter/download_model.py --archive /path/to/rxn_filter_metadata.zip
```

将最后的路径替换为自己的下载文件路径，含空格时加双引号。不要解压、加载包里的另一个 `.pkl`；本实验不需要它。下载失败时没有有效模型可供推理，应先解决下载问题，不能使用随机初始化模型代替。

## 4. 接入主案例的真实反应

本例对应 Organic Syntheses 的 [Photoexcited Nitroarenes for the Anaerobic Cleavage of Alkenes](https://www.orgsyn.org/demo.aspx?prep=v102p0114)。结构对应：

| 角色 | 来源中的化合物 | 本实验 SMILES |
|---|---|---|
| 烯烃反应物 | 1,1-diphenylethene | `C=C(c1ccccc1)c1ccccc1` |
| 含氮芳香反应组分 | 4-nitrobenzonitrile | `N#Cc1ccc([N+](=O)[O-])cc1` |
| 产物 | benzophenone | `O=C(c1ccccc1)c1ccccc1` |

这里的结构映射是明确给出的教学参考。实际接前面阶段时，先检查化合物身份是否已经解析；对未解析、混合物或泛指名称，保留待复核状态，不强行拼成反应 SMILES。SMILES 的文本顺序可能不同，但应表示相同结构。

在仓库根目录运行（Windows/macOS 均可直接用这一行）：

```bash
python optional/rxn_filter/adapter.py --checkpoint optional/rxn_filter/models/rxn_filter_2025.pt --reaction-smiles "C=C(c1ccccc1)c1ccccc1.N#Cc1ccc([N+](=O)[O-])cc1>>O=C(c1ccccc1)c1ccccc1" --cutoff 0.5 --output optional/rxn_filter/outputs/cleavage.json
```

预期 JSON 中 `plausibility_score` 约为 **0.80167**，`needs_review` 为 **false**，`device` 为 **cpu**。允许不同平台浮点结果在末尾有小量差异。输出中的 `needs_review=false` 只表示没有低于所选阈值，不表示该记录已经通过事实核验。

命令可能显示 RDKit 的 `DEPRECATION WARNING: please use MorganGenerator`。本实验保留作者使用的指纹入口以方便核对，这条提示本身不代表运行失败。

## 5. 做一次有意义的对照

将同一条命令的 `--cutoff 0.5` 改成 `--cutoff 0.9`，输出文件改为 `optional/rxn_filter/outputs/cleavage_cutoff09.json`，再次运行。

预期：分数仍约 **0.80167**，但 `needs_review` 变为 **true**。这条反应仍有真实文献依据，阈值改变没有改变实验事实。

回答并提交：

1. 为什么调高阈值会将这条已报道反应标记为待复核？
2. 如果把记录中的温度或产率改错，模型为何可能给出完全相同的分数？
3. 哪些检查必须回到主线的原文参考、ORD 和修订记录中完成？

保存两份 JSON 与简短解释，**不要按低分删除原记录，也不要依据分数补造缺失条件**。评分模型的训练样本含生成负例，分数不是实验成功概率的独立证明。

## 6. 验收与错误处理

```bash
python -m unittest discover -s optional/rxn_filter -p "test_adapter.py" -v
```

应通过 3 个检查：未解析/不完整 SMILES 被拒绝；错误权重在反序列化前被拒绝；改变的模型包被拒绝。另以第 4、5 步的实际权重推理完成数值验收。

| 情况 | 处理 |
|---|---|
| `No module named torch` | 确认正在使用选做环境，再运行安装命令 |
| 下载连接超时 | 使用 `--mirror` 或手动下载后 `--archive`；不关闭证书校验 |
| `SHA256 mismatch` | 不继续运行该文件，重新获取固定权重，或检查是否拿到了别的模型 |
| `not valid SMILES` | 回到实体解析阶段检查输入；化学名称不能直接充当 SMILES |
| 低分但原文有明确实验 | 标记复核并保留原记录，不自动改写为错误/失败 |
| 首次导入较慢 | 本机首次加载 RDKit/PyTorch 可能慢于后续调用；等待导入完成 |

返回必做实验前，运行 `deactivate`，再激活主线环境。
