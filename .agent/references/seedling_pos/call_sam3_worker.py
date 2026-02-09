import subprocess
import json
import numpy as np
import sys

# 确保主环境的 numpy 版本是 >= 2.0
# print(f"Main App using NumPy version: {np.__version__}")

def call_sam_worker(sam_env_python_path, worker_script_path, image_list, prompt, bpe_path=None, ckpt_path=None, temp_dir=None):
    """
    使用 subprocess 调用隔离环境中的 SAM worker 脚本。
    
    :param sam_env_python_path: SAM 虚拟环境的 Python 解释器路径。
    :param worker_script_path: sam3_wrap.py 脚本的路径。
    :param image_list: 要处理的图片路径列表。
    :param prompt: 用于分割的文本提示。
    :param bpe_path: (可选) BPE 词汇文件的路径。
    :param ckpt_path: (可选) SAM3 模型检查点的路径。
    :return: 从 worker 返回的分割掩码数据。
    """
    # 确保 image_list 是一个列表
    if isinstance(image_list, str):
        image_list = [image_list]

    command = [
        sam_env_python_path,
        worker_script_path,
        '--image_list', *image_list,
        '--prompt', prompt,
    ]

    if bpe_path:
        command.extend(['--bpe_path', bpe_path])
    if ckpt_path:
        command.extend(['--ckpt_path', ckpt_path])
    if temp_dir:
        command.extend(['--temp_dir', temp_dir])
    
    print(f"Executing command: {' '.join(command)}")
    
    # 执行命令并捕获输出
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    
    # 检查是否有错误
    if result.returncode != 0:
        print("Error from worker:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"SAM worker script failed with exit code {result.returncode}")

    # 解析 worker 的 JSON 输出
    try:
        # worker脚本可能会打印一些调试信息，我们只取最后一行JSON输出
        last_line = result.stdout.strip().split('\n')[-1]
        output_data = json.loads(last_line)
        if output_data.get("status") == "error":
             raise RuntimeError(f"SAM worker returned an error: {output_data.get('message')}")
        return output_data
    except (json.JSONDecodeError, IndexError) as e:
        print("Failed to decode JSON from worker output:", file=sys.stderr)
        print("Worker stdout:", result.stdout, file=sys.stderr)
        raise e

if __name__ == "__main__":
    # --- 配置 ---
    # !! 重要：请根据你的实际路径修改 !!
    SAM_ENV_PYTHON = "./env_sam/bin/python" # Linux/macOS
    # SAM_ENV_PYTHON = ".\\env_sam\\Scripts\\python.exe" # Windows
    # 注意：worker 脚本现在是 sam3_wrap.py
    WORKER_SCRIPT = "../18_sam3_word_seg/sam3_wrap.py"
    TEST_IMAGE_PATHS = ["./my_test_image.jpg", "./another_image.png"] # 假设有测试图片
    TEST_PROMPT = "a specific object"

    try:
        # 调用 worker
        sam_result = call_sam_worker(
            sam_env_python_path=SAM_ENV_PYTHON,
            worker_script_path=WORKER_SCRIPT,
            image_list=TEST_IMAGE_PATHS,
            prompt=TEST_PROMPT
        )
        
        # 在主程序中处理结果
        masks_array = np.array(sam_result['masks'], dtype=np.uint8)
        
        print("\n--- Result in Main App ---")
        print(f"Successfully received masks from worker.")
        print(f"Masks shape: {masks_array.shape}")
        print(f"Masks dtype: {masks_array.dtype}")
        
        # 在这里继续使用 masks_array 和其他需要 numpy>=2.0 的库进行后续处理
        # ...
        
    except (RuntimeError, FileNotFoundError) as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the virtual environment paths and script paths are correct.")
