# GPU/CUDA 环境配置指南

本指南介绍如何配置 GPU/CUDA 环境以使用 A 股量化交易平台的深度学习功能。

## 目录

- [GPU/CUDA 环境配置指南](#gpucuda-环境配置指南)
  - [目录](#目录)
  - [概述](#概述)
  - [硬件要求](#硬件要求)
  - [环境配置](#环境配置)
    - [方案一：NVIDIA CUDA 12.8（推荐）](#方案一nvidia-cuda-128推荐)
    - [方案二：NVIDIA CUDA 11.8](#方案二nvidia-cuda-118)
    - [方案三：其他国产芯片](#方案三其他国产芯片)
  - [验证安装](#验证安装)
  - [常见问题](#常见问题)

## 概述

A 股量化交易平台支持以下 GPU 加速功能：

- **深度学习模型训练**：PatchTST、TimesNet、iTransformer 等时间序列模型
- **表格数据模型**：TabNet、XGBoost、LightGBM、CatBoost
- **大语言模型**：FinBERT、FINANCE-LLAMA3 等金融 LLM

## 硬件要求

### 最低配置
- GPU：NVIDIA GTX 1660 Super / RTX 3060（6GB 显存）
- CPU：Intel i5 / AMD Ryzen 5
- 内存：16GB
- 存储：50GB 可用空间

### 推荐配置
- GPU：NVIDIA RTX 3080 / 4080 / 4090（16GB+ 显存）
- CPU：Intel i7 / AMD Ryzen 7
- 内存：32GB+
- 存储：100GB+ SSD

### 高端配置
- GPU：NVIDIA RTX 4090 / A100 / H100（24GB+ 显存）
- CPU：Intel i9 / AMD Ryzen 9
- 内存：64GB+
- 存储：1TB+ NVMe SSD

## 环境配置

### 方案一：NVIDIA CUDA 12.8（推荐）

这是最推荐的配置，支持最新的深度学习模型。

#### 1. 检查 GPU 支持

```bash
# 检查 NVIDIA GPU
nvidia-smi

# 应该显示类似以下输出：
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 535.54.03    Driver Version: 535.54.03    CUDA Version: 12.2     |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# | Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
# |                               |                      |              MIG M. |
# |===============================+======================+======================|
# |   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
# |  0%   45C    P8    15W / 250W |   1234MiB / 12288MiB |      0%      Default |
# +-------------------------------+----------------------+----------------------+
```

#### 2. 安装 CUDA 12.8

```bash
# 下载 CUDA 12.8
wget https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_570.86.10_linux.run

# 安装 CUDA
sudo sh cuda_12.8.0_570.86.10_linux.run

# 配置环境变量
echo 'export CUDA_HOME=/usr/local/cuda-12.8' >> ~/.bashrc
echo 'export PATH=$CUDA_HOME/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

#### 3. 安装 cuDNN（可选但推荐）

```bash
# 下载 cuDNN 8.9.7 for CUDA 12.x
# 访问 https://developer.nvidia.com/cudnn 下载

# 解压并安装
tar -xzvf cudnn-linux-x86_64-8.9.7.29_cuda12-archive.tar.xz
sudo cp cudnn-linux-x86_64-8.9.7.29_cuda12-archive/include/* /usr/local/cuda-12.8/include/
sudo cp cudnn-linux-x86_64-8.9.7.29_cuda12-archive/lib/* /usr/local/cuda-12.8/lib64/
sudo chmod a+r /usr/local/cuda-12.8/include/* /usr/local/cuda-12.8/lib64/*
```

#### 4. 安装 PyTorch with CUDA 12.8

```bash
# 使用 pip 安装
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 或使用 conda 安装
conda install pytorch torchvision torchaudio pytorch-cuda=12.8 -c pytorch -c nvidia
```

#### 5. 验证 CUDA

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

### 方案二：NVIDIA CUDA 11.8

适用于旧版 GPU 或特定需求。

#### 1. 安装 CUDA 11.8

```bash
# 下载 CUDA 11.8
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run

# 安装 CUDA
sudo sh cuda_11.8.0_520.61.05_linux.run

# 配置环境变量
echo 'export CUDA_HOME=/usr/local/cuda-11.8' >> ~/.bashrc
echo 'export PATH=$CUDA_HOME/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

#### 2. 安装 PyTorch with CUDA 11.8

```bash
# 使用 pip 安装
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 或使用 conda 安装
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

### 方案三：其他国产芯片

#### 3.1 摩尔线程（Moore Threads）

```bash
# 安装 MUSA SDK
# 访问 https://www.mthreads.com/musa 下载安装

# 安装 PyTorch with MUSA
pip install torch torchvision torchaudio --index-url https://download.mthreads.com/musa/2024.1.0/
```

#### 3.2 华为昇腾（Ascend）

```bash
# 安装 CANN Toolkit
# 访问 https://www.hiascend.com/software/cann 下载安装

# 安装 PyTorch with Ascend
pip install torch torchvision torchaudio --index-url https://download.ascend.com/pytorch/2.1.0/
```

#### 3.3 寒武纪（Cambricon）

```bash
# 安装 MLU SDK
# 访问 https://www.cambricon.com/download 下载安装

# 安装 PyTorch with MLU
pip install torch torchvision torchaudio --index-url https://download.cambricon.com/pytorch/2.1.0/
```

## 验证安装

### 1. 检查 CUDA

```bash
# 检查 CUDA 编译器
nvcc --version

# 应该显示：
# nvcc: NVIDIA (R) Cuda compiler driver
# Copyright (c) 2005-2024 NVIDIA Corporation
# Built on [date]
# Cuda compilation tools, release 12.8, V12.8.93
```

### 2. 检查 PyTorch

```python
import torch

# 检查 CUDA 可用性
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")

# 检查具体 GPU
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"  Total memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
```

### 3. 运行测试

```bash
cd /home/whqwill/code/a-stock-quant
python -c "
import torch
from core.ts_models import PatchTSTModel, TimesNetModel

# 检查 GPU
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f'Using device: {device}')

# 创建模型
model = PatchTSTModel(input_len=96, output_len=24)
print('Model created successfully')

# 移动到 GPU
if device == 'cuda':
    model = model.to(device)
    print('Model moved to GPU')
"
```

## 常见问题

### Q1: CUDA 版本不匹配

**问题**：`RuntimeError: CUDA driver version is insufficient for CUDA runtime version`

**解决方案**：

```bash
# 检查驱动版本
nvidia-smi

# 确保驱动版本 >= CUDA 版本
# CUDA 12.x 需要驱动 >= 525
# CUDA 11.x 需要驱动 >= 450

# 更新驱动（Ubuntu）
sudo apt update
sudo apt install nvidia-driver-535
sudo reboot
```

### Q2: 显存不足

**问题**：`CUDA out of memory`

**解决方案**：

```python
# 减小 batch size
batch_size = 16  # 从 64 减小到 16

# 减小模型大小
model = PatchTSTModel(
    input_len=96,
    output_len=24,
    hidden_dim=128,  # 从 256 减小到 128
    num_layers=2     # 从 4 减小到 2
)

# 使用梯度累积
# 在训练循环中
optimizer.zero_grad()
for i, (x, y) in enumerate(dataloader):
    loss = model(x, y)
    loss.backward()
    if (i + 1) % 4 == 0:  # 每 4 个 batch 更新一次
        optimizer.step()
        optimizer.zero_grad()
```

### Q3: 多 GPU 使用

```python
import torch
import torch.nn as nn

# 检查可用 GPU
device_count = torch.cuda.device_count()
print(f"Available GPUs: {device_count}")

# 使用 DataParallel
if device_count > 1:
    model = nn.DataParallel(model)

# 使用 DistributedDataParallel（推荐）
from torch.nn.parallel import DistributedDataParallel
model = DistributedDataParallel(model)
```

### Q4: CPU fallback

**问题**：模型在 CPU 上运行，速度慢

**解决方案**：

```python
import torch

# 确保模型和数据在同一设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)
data = data.to(device)

# 检查模型参数
for param in model.parameters():
    print(param.device)  # 应该显示 cuda:0
```

### Q5: 国产芯片兼容性

**问题**：使用国产芯片时模型无法运行

**解决方案**：

```python
# 摩尔线程
import musa
device = torch.device('musa' if musa.is_available() else 'cpu')

# 华为昇腾
import torch_npu
device = torch.device('npu' if torch_npu.npu.is_available() else 'cpu')

# 寒武纪
import torch_mlu
device = torch.device('mlu' if torch_mlu.is_available() else 'cpu')
```

## 性能优化建议

### 1. 使用混合精度训练

```python
import torch

# 启用自动混合精度
scaler = torch.cuda.amp.GradScaler()

with torch.cuda.amp.autocast():
    output = model(input)
    loss = criterion(output, target)

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

### 2. 启用 cudnn benchmark

```python
import torch

if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
```

### 3. 数据加载优化

```python
from torch.utils.data import DataLoader

dataloader = DataLoader(
    dataset,
    batch_size=64,
    num_workers=8,  # 根据 CPU 核心数调整
    pin_memory=True,  # 加速 GPU 数据传输
    persistent_workers=True  # 保持 worker 进程
)
```

## 总结

- **推荐配置**：NVIDIA CUDA 12.8 + PyTorch 2.0+
- **最低配置**：NVIDIA CUDA 11.8 + PyTorch 2.0+
- **国产芯片**：根据具体芯片类型安装对应 SDK
- **显存要求**：至少 6GB，推荐 16GB+

详细配置请参考各芯片厂商的官方文档。
