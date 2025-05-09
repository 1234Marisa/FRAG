import os
import json
from datasets import load_dataset

file_path = 'data/ultrachat_200k/ultrachat_200k_train_gen.jsonl' 

# 下载数据集
# # 1. 设置保存路径
# save_dir = os.path.join("data", "ultrachat_200k")
# os.makedirs(save_dir, exist_ok=True)
# # 2. 加载 stingning/ultrachat 数据集
# dataset = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_gen")
# # 3. 转换为列表格式
# data_list = [example for example in dataset]
# # 4. 保存为 JSON 文件
# save_path = os.path.join(save_dir, "ultrachat_200k_train_gen.json")
# with open(save_path, "w", encoding="utf-8") as f:
#     json.dump(data_list, f, ensure_ascii=False, indent=2)
# print(f"✅ 数据已保存至：{save_dir}")




# 将jso文件转换为jsonl文件
# 如果是 JSON 数组（整个文件是一个 list）
# with open(file_path, 'r', encoding='utf-8') as f:
#     data = json.load(f)
# with open('data/ultrachat_200k/ultrachat_200k_train_gen.jsonl', 'w', encoding='utf-8') as f:
#     for item in data:
#         f.write(json.dumps(item, ensure_ascii=False) + '\n')

# 打印前100条数据
# max_prompt_length = 200  # 最大允许的字符数
# max_count = 100 # 要打印的条数

# count = 0
# with open(file_path, 'r', encoding='utf-8') as f:
#     for line in f:
#         try:
#             item = json.loads(line)
#             prompt = item.get('prompt', '')
#             if isinstance(prompt, str) and len(prompt) <= max_prompt_length:
#                 count += 1
#                 print(f"\n【第 {count} 项】")
#                 print("Prompt:", prompt)
#                 if count >= max_count:
#                     break
#         except json.JSONDecodeError:
#             continue  # 跳过损坏行

output_file = 'data/ultrachat_200k/short_prompt_ultrachat_200k_train_gen.jsonl'
max_prompt_length = 300  # 最大字符数
max_count = 3000  # 最多保存多少条（可选）
count = 0
with open(file_path, 'r', encoding='utf-8') as fin, \
     open(output_file, 'w', encoding='utf-8') as fout:

    for line in fin:
        try:
            item = json.loads(line)
            prompt = item.get('prompt', '')
            if isinstance(prompt, str) and len(prompt) <= max_prompt_length:
                json_line = json.dumps({"prompt": prompt.strip()}, ensure_ascii=False)
                fout.write(json_line + '\n')
                count += 1
                if count >= max_count:
                    break
        except json.JSONDecodeError:
            continue

print(f"✅ 共保存 {count} 条 prompt 长度 ≤ {max_prompt_length} 的条目到 {output_file}")














