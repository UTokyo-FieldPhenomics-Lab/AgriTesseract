import os
import colorsys
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import numpy as np
import torch
import torchvision
from PIL import Image
from tqdm import tqdm

import matplotlib
matplotlib.use('Agg')  # 必须在 import pyplot 之前

import matplotlib.pyplot as plt
import random

from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor

# -----------------------------------------------------------------------------
# 1. 切片工具函数 (Slicing Function)
# -----------------------------------------------------------------------------

def slice_image(
    image_path: str,
    slice_height: int = 640,
    slice_width: int = 640,
    overlap_height_ratio: float = 0.2,
    overlap_width_ratio: float = 0.2,
) -> List[Dict]:
    """
    将图像切分为多个重叠的切片。
    
    Args:
        image_path: 图片路径
        slice_height: 切片高度
        slice_width: 切片宽度
        overlap_height_ratio: 高度重叠率 (0-1)
        overlap_width_ratio: 宽度重叠率 (0-1)
        
    Returns:
        List[Dict]: 包含切片图像(PIL)、偏移量、以及是否位于原图边缘的信息
    """
    # 读取图像 (OpenCV 读取为 BGR, 转为 RGB)
    image_cv = cv2.imread(image_path)
    if image_cv is None:
        raise FileNotFoundError(f"Image not found at {image_path}")
    
    image_h, image_w, _ = image_cv.shape
    image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
    
    # 计算步长
    stride_h = int(slice_height * (1 - overlap_height_ratio))
    stride_w = int(slice_width * (1 - overlap_width_ratio))
    
    slice_results = []
    
    # 开始滑窗，同时记录行列索引
    y = 0
    row_idx = 0
    n_cols = 0  # 记录列数 (第一行时计算)
    
    while y < image_h:
        x = 0
        col_idx = 0
        
        while x < image_w:
            # 计算当前切片的坐标
            x1 = x
            y1 = y
            x2 = min(x + slice_width, image_w)
            y2 = min(y + slice_height, image_h)
            
            # 如果是最后一块，且不足一个切片大小，通常有两种策略：
            # 1. Pad 补全 (保持坐标不变)
            # 2. 回退 (Shift back) 保证切片大小固定 (推荐，利于模型推理)
            
            real_x1 = x1
            real_y1 = y1
            
            # 如果到达右边界，回退 x
            if x2 - x1 < slice_width:
                real_x1 = max(0, image_w - slice_width)
                x2 = image_w # 强制对齐边缘
                
            # 如果到达下边界，回退 y
            if y2 - y1 < slice_height:
                real_y1 = max(0, image_h - slice_height)
                y2 = image_h
            
            # 提取切片
            patch = image_rgb[real_y1:y2, real_x1:x2]
            
            # 转为 PIL Image
            pil_patch = Image.fromarray(patch)
            
            # 记录该切片是否触碰到原图的边缘 (用于后续过滤逻辑)
            is_edge = {
                'left': real_x1 == 0,
                'top': real_y1 == 0,
                'right': x2 == image_w,
                'bottom': y2 == image_h
            }
            
            slice_results.append({
                "image": pil_patch,
                "offset": (real_x1, real_y1), # (x, y) 偏移量
                "size": (x2 - real_x1, y2 - real_y1), # 实际切片大小
                "is_edge": is_edge,
                "row": row_idx,  # 行索引 (从0开始)
                "col": col_idx,  # 列索引 (从0开始)
            })
            
            col_idx += 1
            
            # 更新 x
            if x2 == image_w:
                break
            x += stride_w
        
        # 第一行结束时记录列数
        if row_idx == 0:
            n_cols = col_idx
            
        row_idx += 1
        
        # 更新 y
        if y2 == image_h:
            break
        y += stride_h
    
    n_rows = row_idx
    grid_shape = (n_rows, n_cols)  # (行数, 列数)
        
    return slice_results, (image_h, image_w), grid_shape

# -----------------------------------------------------------------------------
# 2. SAM3 模型封装 (Model Wrapper)
# -----------------------------------------------------------------------------


class Sam3Model:
    def __init__(self, 
                 model_path: str,
                 text_prompt: str = "object",
                 sam3_conf_thresh: float = 0.5,
                 device: str = "cuda"): 
      
        self.text_prompt = text_prompt
        self.sam3_conf = sam3_conf_thresh
        self.device = device
        self.model_dir = model_path
        self.model = None
        self.processor = None
      
    def load_model(self):
        """加载 Sam3ONNXInference 引擎"""
        # 注意：此处假设 build_sam3_image_model 和 Sam3Processor 已导入
        # 为了代码不报错，这里需要你确保环境中有这些定义
        try:
            from pathlib import Path
            # 模拟导入，实际使用请取消注释并确保路径正确
            # from sam3_lib import build_sam3_image_model, Sam3Processor 
            pass 
        except ImportError:
            print("Warning: SAM3 libraries not found. Ensure imports are correct.")

        model_dir = Path(self.model_dir)
        
        # 伪代码：实际调用你的 SAM3 构建函数
        self.model = build_sam3_image_model(
            bpe_path=str(model_dir / "bpe_simple_vocab_16e6.txt.gz"), 
            device=self.device,
            checkpoint_path=str(model_dir / "sam3.pt")
        )

        self.model.to(self.device)
        self.model.eval()
        self.processor = Sam3Processor(self.model, device=self.device)
        print(f"SAM3 Model loaded successfully with prompt: '{self.text_prompt}'")

    def perform_inference(self, image_pil: Image.Image) -> Dict:
        """
        对单张切片进行推理
        """
        if self.model is None:
            self.load_model()

        # set_image 需要 PIL 或者 numpy，根据你的库定义
        # 假设 processor 内部处理缩放和归一化
        inference_state = self.processor.set_image(image_pil)
        
        # 传入 box_threshold 和 text_threshold 等参数控制置信度
        results = self.processor.set_text_prompt(
            prompt=self.text_prompt,
            state=inference_state, 
        )
        
        # 确保 results 都在 GPU 上，方便后续处理
        return results

# -----------------------------------------------------------------------------
# 3. 结果合并与处理逻辑 (Merge Logic)
# -----------------------------------------------------------------------------

def filter_border_boxes(boxes, scores, masks, slice_w, slice_h, is_edge, border_thr=2):
    """
    过滤掉紧贴切片边缘的框，除非该边缘也是原图的边缘。

    boexes: Tensor (N, 4)
    scores: Tensor (N)
    masks: Tensor (N, H_mask, W_mask)
    """

    if boxes.numel() == 0:
        return boxes, scores, masks

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    # keep: Tensor (N,) bool
    keep = torch.ones(len(boxes), dtype=torch.bool, device=boxes.device)

    # 如果不是原图左边缘，且框紧贴切片左边 -> 丢弃
    if not is_edge['left']:
        keep &= (x1 > border_thr)
    
    # 如果不是原图上边缘 -> 丢弃
    if not is_edge['top']:
        keep &= (y1 > border_thr)
        
    # 如果不是原图右边缘 -> 丢弃
    if not is_edge['right']:
        keep &= (x2 < slice_w - border_thr)
        
    # 如果不是原图下边缘 -> 丢弃
    if not is_edge['bottom']:
        keep &= (y2 < slice_h - border_thr)

    return keep


def nms_with_ios(boxes, scores, iou_threshold=0.5, ios_threshold=0.95):
    """
    先进行标准的 IoU NMS，处理普通重叠。
    再进行 IoS (Intersection over Smaller) 处理，专门去除“大框包小框”的冗余检测。
    
    Args:
        boxes: (N, 4) [x1, y1, x2, y2]
        scores: (N,)
        iou_threshold: 标准 NMS 阈值
        ios_threshold: 包含关系阈值 (建议 0.8 或 0.9)
    
    Returns:
        keep: 保留的索引
    """
    # 1. 先跑一次标准的 NMS (基于 IoU)
    # 这能快速去除大部分高度重叠的框
    keep = torchvision.ops.nms(boxes, scores, iou_threshold)
    
    # 如果剩下的框很少，直接返回
    if len(keep) < 2:
        return keep
        
    # 提取经过初步筛选的框
    nms_boxes = boxes[keep]
    nms_scores = scores[keep]
    
    # 2. 计算 IoS (Intersection over Smaller)
    # 这是一个 O(N^2) 的操作，但因为 NMS 已经过滤了大部分，所以 N 通常很小，速度很快
    
    # 计算每个框的面积
    x1 = nms_boxes[:, 0]
    y1 = nms_boxes[:, 1]
    x2 = nms_boxes[:, 2]
    y2 = nms_boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    
    # 这里的逻辑是：对于每一对框，检查 IoS
    # 为了保持 pytorch 的高效，我们使用广播机制
    
    # 排序：按分数从高到低 (NMS 已经排过了，但为了保险)
    # 实际上 torchvision.ops.nms 返回的 keep 已经是按 score 排序的了
    
    n = len(nms_boxes)
    suppressed = torch.zeros(n, dtype=torch.bool, device=boxes.device)
    
    for i in range(n):
        if suppressed[i]:
            continue
            
        # 当前框与其他所有后续框比较
        # inter_x1 = max(x1[i], x1[i+1:])
        inter_x1 = torch.max(x1[i], x1[i+1:])
        inter_y1 = torch.max(y1[i], y1[i+1:])
        inter_x2 = torch.min(x2[i], x2[i+1:])
        inter_y2 = torch.min(y2[i], y2[i+1:])
        
        inter_w = (inter_x2 - inter_x1).clamp(min=0)
        inter_h = (inter_y2 - inter_y1).clamp(min=0)
        
        inter_area = inter_w * inter_h
        
        # 关键点：分母使用 min(area[i], area[j])
        # 我们比较的是 j (后面的框) 是否被 i (当前高分框) 包含，或者 i 是否被 j 包含
        smaller_area = torch.min(areas[i], areas[i+1:])
        
        ios = inter_area / (smaller_area + 1e-6)
        
        # 如果 IoS 大于阈值，说明存在严重的包含关系
        # 因为我们已经按分数排序了，i 的分数 >= j 的分数
        # 所以我们抑制 j (后续的框)
        
        # 找到满足条件的索引
        override_indices = torch.where(ios > ios_threshold)[0]
        
        # 注意：override_indices 是相对于 i+1 的偏移量
        if len(override_indices) > 0:
            suppressed[i + 1 + override_indices] = True
            
    return keep[~suppressed]

def run_sliding_window_inference(
    model: Sam3Model,
    image_path: str,
    slice_params: Dict,
    iou_threshold: float = 0.5, 
    ios_threshold: float = 0.95,
    show: bool = False,
    save_path: str = None,
):
    """
    主函数：切片 -> 推理 -> 坐标映射 -> 过滤 -> NMS -> 合并
    全程不保留全图 Mask Tensor，极大节省显存。
    """
    # 1. 切片
    print(f"Slicing image: {image_path}...")
    slices, (orig_h, orig_w), grid_shape = slice_image(image_path, **slice_params)
    print(f"Generated {len(slices)} slices (grid: {grid_shape[0]} rows x {grid_shape[1]} cols).")

    all_boxes = []
    all_scores = []
    # 关键修改：all_masks 现在存储的是 List[Tensor]，每个 Tensor 是一个小 Crop
    all_masks_crops = [] 

    # 用于可视化的数据收集
    slice_vis_data = [] 
    
    # 2. 遍历切片推理
    progress = tqdm(slices, desc="Inferencing on slices")
    for slc in progress:
        pil_img = slc['image']
        offset_x, offset_y = slc['offset']
        slice_w, slice_h = slc['size']
        
        # 推理
        results = model.perform_inference(pil_img)

        pred_boxes = results['boxes']  # (N, 4)
        pred_scores = results['scores'] # (N)
        pred_masks = results['masks'] # (N, 1, H, W)

        progress.set_description_str(f"Inferencing on slices (detected: {len(pred_masks)})")

        
        # 提取结果 (假设 results 里的 tensor 都在 GPU)
        # --- 维度整理 ---
        if pred_boxes.dim() == 3: pred_boxes = pred_boxes.squeeze(0)
        if pred_scores.dim() == 2: pred_scores = pred_scores.squeeze(0)
        if pred_masks.dim() == 4:
            if pred_masks.shape[1] == 1: pred_masks = pred_masks.squeeze(1)
            elif pred_masks.shape[0] == 1: pred_masks = pred_masks.squeeze(0)
        # 现在 pred_masks 是 (N, H, W)

        # 即使没有检测到目标，如果开启可视化，也需要记录空结果以便画出切片
        if pred_boxes is None or pred_boxes.numel() == 0:
            if show or save_path is not None:
                slice_vis_data.append({
                    'image': pil_img,
                    'is_edge': slc['is_edge'],
                    'row': slc['row'],
                    'col': slc['col'],
                    'keep_boxes': torch.tensor([]),
                    'keep_scores': torch.tensor([]),
                    'keep_masks': torch.tensor([]),
                    'rm_boxes': torch.tensor([]),
                    'rm_scores': torch.tensor([]),
                    'rm_masks': torch.tensor([]),
                })
            continue
            
        # 3. 过滤边界框 (Border Filtering)
        # 目的：丢弃切片边缘截断的目标，依赖重叠的相邻切片来完整检测
        keep_indices = filter_border_boxes(
            pred_boxes, pred_scores, pred_masks, 
            slice_w, slice_h, slc['is_edge']
        )

        # pred_boxes: Tensor (N, 4)
        # pred_scores: Tensor (N)
        # pred_masks: Tensor (N, H_mask, W_mask)
        keep_boxes = pred_boxes[keep_indices]
        keep_scores = pred_scores[keep_indices]
        keep_masks = pred_masks[keep_indices]
        
        rm_boxes = pred_boxes[~keep_indices]
        rm_scores = pred_scores[~keep_indices]
        rm_masks = pred_masks[~keep_indices]
        
        if len(keep_boxes) == 0:
            continue

        # --- 关键修改：立即裁剪 Mask 并转存 CPU ---
        # 这一步将显存占用从 O(H*W) 降到了 O(Object_Area)
        current_slice_crops = []
        
        # 确保 mask 是 bool 类型节省空间
        if keep_masks.dtype != torch.bool:
            keep_masks = keep_masks > 0
            
        for k in range(len(keep_boxes)):
            # 获取局部坐标的 box
            bx1, by1, bx2, by2 = keep_boxes[k].int()
            
            # 边界保护
            bx1 = max(0, bx1.item()); by1 = max(0, by1.item())
            bx2 = min(slice_w, bx2.item()); by2 = min(slice_h, by2.item())
            
            # 裁剪 (Clone 是必须的，否则显存不会释放)
            # 保持 (1, H, W) 格式方便后续处理，或者 (H, W) 也可以
            # 这里存为 (H_crop, W_crop)
            crop = keep_masks[k, by1:by2, bx1:bx2].clone().cpu()
            current_slice_crops.append(crop)
            
        # 显式释放大 Mask 显存
        del pred_masks, keep_masks, results
        # torch.cuda.empty_cache() # 如果显存极度紧张可取消注释，但会拖慢速度

        # --- 收集可视化数据 ---
        if show or save_path is not None:
            slice_vis_data.append({
                'image': pil_img,
                'is_edge': slc['is_edge'],
                'row': slc['row'],
                'col': slc['col'],
                'keep_boxes': keep_boxes.detach().cpu(),
                'keep_scores': keep_scores.detach().cpu(),
                'keep_masks': current_slice_crops, # 存 crop
                'rm_boxes': rm_boxes.detach().cpu(),
                'rm_scores': rm_scores.detach().cpu(),
                'rm_masks': rm_masks.detach().cpu(),
            })

        # 4. 坐标映射 (Local to Global)
        # Box: [x1, y1, x2, y2]
        global_boxes = keep_boxes.clone()
        global_boxes[:, 0] += offset_x
        global_boxes[:, 1] += offset_y
        global_boxes[:, 2] += offset_x
        global_boxes[:, 3] += offset_y
        
        all_boxes.append(global_boxes)
        all_scores.append(keep_scores)
        all_masks_crops.extend(current_slice_crops) # 扁平化列表
        

    if not all_boxes:
        print("No objects detected.")
        empty_res = {
            'original_height': orig_h, 'original_width': orig_w,
            'boxes': torch.empty((0, 4), device=model.device),
            'scores': torch.empty((0), device=model.device),
            'masks': [] # 空列表
        }
        return empty_res
    

    # --- 全局 NMS ---
    global_boxes_cat = torch.cat(all_boxes, dim=0)
    global_scores_cat = torch.cat(all_scores, dim=0)
    
    # 5. 全局 NMS (Non-Maximum Suppression)
    print(f"Running NMS with IoS on {len(global_boxes_cat)} detections...")
    keep_indices = nms_with_ios(
        global_boxes_cat, 
        global_scores_cat, 
        iou_threshold=iou_threshold, 
        ios_threshold=ios_threshold, 
    )
    
    # 保留 NMS 后的结果
    final_boxes = global_boxes_cat[keep_indices]
    final_scores = global_scores_cat[keep_indices]

    # --- 关键修改：重组 Mask ---
    # 不再创建全图 mask，而是直接提取对应的 crop mask
    # keep_indices 是 tensor，我们需要转为 list 索引
    keep_indices_list = keep_indices.cpu().numpy().tolist()
    final_masks_crops = [all_masks_crops[i] for i in keep_indices_list]

    # 构造输出
    final_output = {
        'original_height': orig_h,
        'original_width': orig_w,
        'boxes': final_boxes,           # (N, 4)
        'scores': final_scores,         # (N)
        'masks': final_masks_crops,     # List[Tensor] (N) -> 每个是 (H_crop, W_crop)
        'is_packed': True               # 标记为已压缩格式
    }
    print(f"Inference complete. Found {len(final_boxes)} objects.")


    # 7. 执行可视化
     # --- 可视化 ---
    if show or save_path is not None:
        print("Generating visualization...")
        # 准备数据，确保都在 CPU (mask 已经在 CPU 了)
        final_output_cpu = {
            'boxes': final_output['boxes'].detach().cpu(),
            'scores': final_output['scores'].detach().cpu(),
            'masks': final_output['masks'] # 已经是 List[Tensor(CPU)]
        }
        visualize_results(image_path, slice_vis_data, final_output_cpu, slice_params, grid_shape, show, save_path)
    else:
        print(f"Visualization disabled. show = {show}, save_path = {save_path}")

    return final_output

# -----------------------------------------------------------------------------
# 保存数据和读取
# -----------------------------------------------------------------------------
def pack_masks(boxes, masks):
    """
    将全图 Mask 转换为 BBox 内的局部 Mask 列表。
    
    Args:
        boxes: (N, 4) [x1, y1, x2, y2]
        masks: (N, 1, H, W) 全图 Mask
        
    Returns:
        packed_masks: List[Tensor], 每个元素是 (1, H_box, W_box) 的 bool tensor
    """
    packed_masks = []
    
    # 确保 mask 是 bool 类型以节省空间 (int8 也可以，但 bool 最小)
    if masks.dtype != torch.bool:
        masks = masks > 0
        
    for i in range(len(boxes)):
        x1, y1, x2, y2 = boxes[i].int()
        
        # 裁剪 Mask
        # 注意边界检查，防止 float 转 int 后的细微越界
        h, w = masks.shape[-2:]
        x1 = max(0, x1.item())
        y1 = max(0, y1.item())
        x2 = min(w, x2.item())
        y2 = min(h, y2.item())
        
        # 提取 bbox 区域内的 mask
        # masks[i] shape: (1, H, W)
        crop = masks[i, :, y1:y2, x1:x2].clone()
        
        # 进一步优化：转为稀疏矩阵? 
        # 对于小物体，dense crop 已经很小了，无需 sparse。
        packed_masks.append(crop)
        
    return packed_masks

def unpack_masks(boxes, packed_masks, original_h, original_w):
    """
    将局部 Mask 列表还原为全图 Mask Tensor。
    
    Args:
        boxes: (N, 4)
        packed_masks: List[Tensor]
        original_h: 原图高
        original_w: 原图宽
        
    Returns:
        full_masks: (N, 1, H, W)
    """
    N = len(boxes)
    # 创建全图空 mask
    full_masks = torch.zeros((N, 1, original_h, original_w), dtype=torch.bool)
    
    for i in range(N):
        x1, y1, x2, y2 = boxes[i].int()
        crop = packed_masks[i]
        
        # 即使保存时做了边界检查，还原时最好也校验一下尺寸匹配
        # 因为 float box 转 int 可能有 1px 误差，这里直接用 crop 的尺寸覆盖
        crop_h, crop_w = crop.shape[-2:]
        
        # 修正 y2, x2 以匹配 crop 实际大小
        # 确保不越界
        y2 = min(original_h, y1 + crop_h)
        x2 = min(original_w, x1 + crop_w)
        
        # 赋值
        full_masks[i, :, y1:y2, x1:x2] = crop[:, :y2-y1, :x2-x1]
        
    return full_masks


def save_results(results: dict, save_path: str):
    """
    保存推理结果。
    由于推理函数已经输出了优化后的 masks (List[Tensor])，这里直接保存即可。
    """
    cpu_results = {}
    
    for k, v in results.items():
        if isinstance(v, torch.Tensor):
            cpu_results[k] = v.cpu()
        elif isinstance(v, list):
            # 列表中的 Tensor (masks) 也要确保在 CPU
            if len(v) > 0 and isinstance(v[0], torch.Tensor):
                cpu_results[k] = [x.cpu() for x in v]
            else:
                cpu_results[k] = v
        else:
            cpu_results[k] = v
            
    # 确保标记了 is_packed，方便读取函数识别
    if 'masks' in cpu_results and isinstance(cpu_results['masks'], list):
        cpu_results['masks_in_bbox'] = cpu_results.pop('masks') # 重命名以匹配 load 逻辑
        cpu_results['is_packed'] = True
    
    torch.save(cpu_results, save_path)
    print(f"Optimized results saved to {save_path}")
    

def load_results(load_path: str, device: str = 'cpu', unpack: bool = False):
    """
    读取推理结果。
    
    Args:
        unpack: True 则自动还原为全图 Mask (N, 1, H, W)，方便使用但占内存。
                False 则保留 masks_in_bbox 列表，省内存。
    """
    if not os.path.exists(load_path):
        raise FileNotFoundError(f"{load_path} not found.")
        
    results = torch.load(load_path, map_location=device)
    
    # 检查是否是压缩格式
    if results.get('is_packed', False) and unpack:
        # print("Unpacking masks to full image size...")
        boxes = results['boxes']
        packed_masks = results['masks_in_bbox']
        h = results['original_height']
        w = results['original_width']
        
        # 还原
        full_masks = unpack_masks(boxes, packed_masks, h, w)
        results['masks'] = full_masks.to(device)
        
        # 清理掉压缩数据，保持 dict 干净
        del results['masks_in_bbox']
        del results['is_packed']
    
    return results

# -----------------------------------------------------------------------------
# 辅助函数：可视化绘图工具
# -----------------------------------------------------------------------------
def generate_colors(n):
    """
    生成 N 个高饱和度、高亮度的鲜艳颜色 (R, G, B)。
    使用 HSV 颜色空间来控制亮度和饱和度，避免生成暗色。
    """
    # 使用固定种子，保证同一组数据生成的颜色在多次绘制中一致
    rng = random.Random(42) 
    colors = []
    
    for _ in range(n):
        # 1. 色相 (Hue): 0.0 ~ 1.0 随机，覆盖所有颜色种类
        h = rng.random()
        
        # 2. 饱和度 (Saturation): 0.7 ~ 1.0，保证颜色鲜艳，不发灰
        s = rng.uniform(0.7, 1.0)
        
        # 3. 亮度 (Value): 0.8 ~ 1.0，保证颜色明亮，绝无暗色
        v = rng.uniform(0.8, 1.0)
        
        # 4. 转为 RGB (结果是 0.0~1.0 的浮点数)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        # 5. 映射回 0~255 并转为整数
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
        
    return colors

def draw_dashed_rect(img, pt1, pt2, color, thickness=1, style='dotted', gap=10):
    """
    在 OpenCV 图像上绘制虚线矩形
    """
    dist = gap
    x1, y1 = pt1
    x2, y2 = pt2
    
    # Top line
    for x in range(x1, x2, dist*2):
        cv2.line(img, (x, y1), (min(x+dist, x2), y1), color, thickness)
    # Bottom line
    for x in range(x1, x2, dist*2):
        cv2.line(img, (x, y2), (min(x+dist, x2), y2), color, thickness)
    # Left line
    for y in range(y1, y2, dist*2):
        cv2.line(img, (x1, y), (x1, min(y+dist, y2)), color, thickness)
    # Right line
    for y in range(y1, y2, dist*2):
        cv2.line(img, (x2, y), (x2, min(y+dist, y2)), color, thickness)

def overlay_detections(image, boxes, masks, scores, alpha=0.7, draw_scores=True, same_color:Tuple[int, int, int]|None=None):
    """
    在图像上绘制 BBox, Mask 和 Scores
    image: numpy array (H, W, 3) RGB
    boxes: (N, 4)
    masks: (N, H, W) or (N, 1, H, W) | List( bbox_in_mask Tensor (h, w) )
    scores: (N,)
    draw_scores: bool, 是否绘制分数文本和背景
    same_color: Tuple[int, int, int]|None, 是否使用统一颜色
    """
    out_image = image.copy()
    num_dets = len(boxes)
    if num_dets == 0:
        return out_image
        
    if same_color is None:
        colors = generate_colors(num_dets)
    else:   
        colors = [same_color] * num_dets
    
    # 判断 masks 是否为列表 (即 mask_in_bbox 模式)
    is_crop_mask = isinstance(masks, list)
    
    # 如果是全图 Tensor，确保维度正确
    if not is_crop_mask and isinstance(masks, torch.Tensor) and masks.ndim == 4:
        masks = masks.squeeze(1)
        
    for i in range(num_dets):
        color = colors[i]
        box = boxes[i].int().cpu().numpy()
        score = scores[i].item()
        
        x1, y1, x2, y2 = box
        
        # --- 1. 绘制 Mask ---
        # 提取当前 mask 的 numpy 数据
        if is_crop_mask:
            # masks[i] 是 (1, H_crop, W_crop) 或 (H_crop, W_crop)
            mask_tensor = masks[i]
            if isinstance(mask_tensor, torch.Tensor):
                mask_np = mask_tensor.cpu().numpy()
            else:
                mask_np = mask_tensor # 已经是 numpy
            
            # 统一维度
            if mask_np.ndim == 3: mask_np = mask_np.squeeze(0)
        else:
            # 全图 mask 模式
            mask_np = masks[i].cpu().numpy() # bool or float
            
        # 准备绘制层
        # 如果是 Crop Mask，我们需要只在 ROI 区域操作
        if is_crop_mask:
            # 确保坐标在图像范围内
            h_img, w_img = out_image.shape[:2]
            x1_c = max(0, x1); y1_c = max(0, y1)
            x2_c = min(w_img, x2); y2_c = min(h_img, y2)
            
            w_roi = x2_c - x1_c
            h_roi = y2_c - y1_c
            
            if w_roi > 0 and h_roi > 0:
                # 获取 ROI
                roi = out_image[y1_c:y2_c, x1_c:x2_c]
                
                # 处理 Mask 大小匹配问题 (Box 取整可能导致 1px 误差)
                # 将 mask_np resize 到 roi 大小
                mask_roi = cv2.resize(mask_np.astype(np.uint8), (w_roi, h_roi), interpolation=cv2.INTER_NEAREST)
                mask_roi = mask_roi > 0 # 转回 bool
                
                # 创建彩色 mask 层
                colored_roi = np.zeros_like(roi)
                colored_roi[mask_roi] = color
                
                # 融合
                roi[mask_roi] = cv2.addWeighted(
                    roi[mask_roi], 1 - alpha,
                    colored_roi[mask_roi], alpha,
                    0
                )
                # 放回原图
                out_image[y1_c:y2_c, x1_c:x2_c] = roi
        else:
            # 全图 Mask 模式 (旧逻辑)
            colored_mask = np.zeros_like(out_image)
            mask_bool = mask_np if mask_np.dtype == bool else mask_np > 0
            colored_mask[mask_bool] = color
            
            if mask_bool.any():
                out_image[mask_bool] = cv2.addWeighted(
                    out_image[mask_bool], 1 - alpha, 
                    colored_mask[mask_bool], alpha, 
                    0
                )
            
        # --- 2. 绘制 BBox ---
        cv2.rectangle(out_image, (x1, y1), (x2, y2), color, 2)
        
        # --- 3. 绘制 Score ---
        if draw_scores:
            label = f"{score:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out_image, (x1, y1 - 20), (x1 + w, y1), color, -1)
            cv2.putText(out_image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
    return out_image

def visualize_results(
    original_image_path: str,
    slice_vis_data: List[Dict],
    merged_results: Dict,
    slice_cfg: Dict,
    grid_shape: Tuple[int, int],
    show: bool = False,
    save_path: str = None,
):
    """
    可视化主逻辑
    1. 绘制切片网格 (Subplots) - 按原图布局排列
    2. 绘制最终合并结果
    
    Args:
        grid_shape: (n_rows, n_cols) 原图切片的网格形状
    """
    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # 1. 切片可视化 (Subplots) - 使用原图网格布局
    # -------------------------------------------------
    n_slices = len(slice_vis_data)
    rows, cols = grid_shape  # 使用实际的网格形状

    slice_w = slice_cfg['slice_width']
    slice_h = slice_cfg['slice_height']

    overlap_h_ratio = slice_cfg.get('overlap_height_ratio', 0.2)
    overlap_w_ratio = slice_cfg.get('overlap_width_ratio', 0.2)

    buffer_h = int(slice_h * overlap_h_ratio)
    buffer_w = int(slice_w * overlap_w_ratio)

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4), dpi=300)
    fig.suptitle(f"Slice [W{slice_w}, H{slice_h}] Overlap [H{buffer_h}, W{buffer_w}] ({n_slices} slices, {rows}x{cols})", fontsize=16)
    
    # 确保 axes 是 2D 数组以便通过 row/col 索引
    if rows == 1 and cols == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes[np.newaxis, :]
    elif cols == 1:
        axes = axes[:, np.newaxis]
    

    for data in slice_vis_data:
        row = data['row']
        col = data['col']
        ax = axes[row, col]
        
        img_np = np.array(data['image']) # RGB
        h, w, _ = img_np.shape
        
        # 叠加检测结果
        img_vis = overlay_detections(
            img_np, 
            data['keep_boxes'], 
            data['keep_masks'], 
            data['keep_scores'],
            alpha=0.7
        )

        # 叠加删除结果
        img_vis = overlay_detections(
            img_vis, 
            data['rm_boxes'], 
            data['rm_masks'], 
            data['rm_scores'],
            alpha=0.7,
            same_color=(255, 0, 0),
            draw_scores=False,
        )
        
        # --- 绘制虚线边界 (Overlay Boundary) ---
        # 逻辑：如果某条边不是原图边缘 (is_edge=False)，说明该边有重叠区域
        # 我们画出重叠区域的分界线
        
        is_edge = data['is_edge']
        border_color = (255, 255, 255) # 白色虚线
        
        # 计算重叠像素量
        ov_w = int(w * overlap_w_ratio)
        ov_h = int(h * overlap_h_ratio)
        
        # # 左侧重叠区
        # if not is_edge['left']:
        #     draw_dashed_rect(img_vis, (0, 0), (ov_w, h), border_color)
        
        # # 上侧重叠区
        # if not is_edge['top']:
        #     draw_dashed_rect(img_vis, (0, 0), (w, ov_h), border_color)
            
        # # 右侧重叠区
        # if not is_edge['right']:
        draw_dashed_rect(img_vis, (w - ov_w, 0), (w, h), border_color)
            
        # # 下侧重叠区
        # if not is_edge['bottom']:
        draw_dashed_rect(img_vis, (0, h - ov_h), (w, h), border_color)
            
        ax.imshow(img_vis)
        ax.set_title(f"Slice ({row},{col})", fontsize=10)
        ax.axis('off')
    
    # 隐藏未使用的子图 (如果有)
    for r in range(rows):
        for c in range(cols):
            # 检查是否有对应的 slice 数据
            has_data = any(d['row'] == r and d['col'] == c for d in slice_vis_data)
            if not has_data:
                axes[r, c].axis('off')
            
    plt.tight_layout()
    if show:
        plt.show()
    if save_path:
        plt.savefig(save_path.parent / f"{save_path.stem}_slices{save_path.suffix}", bbox_inches='tight')
        plt.close() # 关闭当前 Figure 释放内存
    
    # -------------------------------------------------
    # 2. 最终合并结果可视化 (带 Score)
    # -------------------------------------------------
    orig_img = cv2.imread(original_image_path)
    orig_img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
    
    # 复制一份用于绘制带分数的图
    final_vis = overlay_detections(
        orig_img.copy(),
        merged_results['boxes'],
        merged_results['masks'],
        merged_results['scores'],
        draw_scores=True
    )
    
    plt.figure(figsize=(12, 10), dpi=300)
    plt.title(f"Final Merged Result (Total Objects: {len(merged_results['boxes'])})")
    plt.imshow(final_vis)
    plt.axis('off')
    if show:
        plt.show()
    if save_path:
        plt.savefig(save_path.parent / f"{save_path.stem}_final{save_path.suffix}", bbox_inches='tight')
        plt.close() # 关闭当前 Figure 释放内存

    # -------------------------------------------------
    # 3. 最终合并结果可视化 (不带 Score, 仅 BBox + Mask)
    # -------------------------------------------------
    if save_path:
        # 再次调用绘制函数，这次 draw_scores=False
        final_vis_noscore = overlay_detections(
            orig_img.copy(), # 使用原始干净的图片
            merged_results['boxes'],
            merged_results['masks'],
            merged_results['scores'],
            draw_scores=False # <--- 关键修改：隐藏分数
        )
        
        plt.figure(figsize=(12, 10), dpi=300)
        # 不带 Title 以保持图片纯净，或者可以加一个简单的 Title
        plt.axis('off')
        plt.imshow(final_vis_noscore)
        
        # 保存为 _final_noscore
        noscore_path = save_path.parent / f"{save_path.stem}_final_noscore{save_path.suffix}"
        plt.savefig(noscore_path, bbox_inches='tight', pad_inches=0) # pad_inches=0 尽量减少白边
        plt.close()
        print(f"Saved no-score visualization to: {noscore_path}")


# -----------------------------------------------------------------------------
# 使用示例
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # 配置
    IMG_PATH = "./test_img/003_full.jpg"
    MODEL_DIR = "weights/sam3"

    img_path = Path(IMG_PATH)
    
    # 初始化模型
    sam3_model = Sam3Model(
        model_path=MODEL_DIR,
        text_prompt="grain", # 针对小目标
        device="cuda"
    )
    
    # 定义切片参数
    slice_cfg = {
        "slice_height": 640,
        "slice_width": 640,
        "overlap_height_ratio": 0.2,
        "overlap_width_ratio": 0.2
    }
    
    # 运行
    # 注意：确保你的环境中安装了 torch, torchvision, opencv-python, pillow
    try:
        # results:
        #  'original_height': int
        #  'original_width': int
        #  'boxes': Tensor (N, 4)
        #  'scores': Tensor (N)
        #  'masks': Tensor (N, 1, H, W)
        results = run_sliding_window_inference(
            model=sam3_model, 
            image_path=IMG_PATH, 
            slice_params=slice_cfg,
            iou_threshold=0.4, # NMS 阈值
            show=True, # 是否可视化
            save_path=f"./demo_output/{img_path.stem}.png"
        )

        print("Result Boxes Shape:", results['boxes'].shape)
        print("Result Mask List len:", len(results['masks']))
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
