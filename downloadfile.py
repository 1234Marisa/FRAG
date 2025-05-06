import os
import json
from datasets import load_dataset

# 1. 设置保存路径
save_dir = os.path.join("data", "ultrachat_200k")
os.makedirs(save_dir, exist_ok=True)

# 2. 加载 stingning/ultrachat 数据集
dataset = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft")

# # 3. 转换为列表格式
# data_list = [example for example in dataset]

# # 4. 保存为 JSON 文件
# save_path = os.path.join(save_dir, "ultrachat_200k.json")
# with open(save_path, "w", encoding="utf-8") as f:
#     json.dump(data_list, f, ensure_ascii=False, indent=2)

print(f"✅ 数据已保存至：{save_dir}")

