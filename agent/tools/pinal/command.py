import re
import argparse
import pandas as pd
from gradio_client import Client

def markdown_to_dataframe(markdown_str):
    # 去除HTML标签
    markdown_str = re.sub(r'<[^>]+>', '', markdown_str)
    
    # 去掉表格中的前后空格和多余的空格，确保每列的对齐
    markdown_str = re.sub(r'\|\s*', '|', markdown_str)  # 去除每行每列开头的空格
    markdown_str = re.sub(r'\s*\|', '|', markdown_str)  # 去除每行每列末尾的空格
    
    # 输出清理后的markdown内容以便调试
    print("Cleaned Markdown:\n", markdown_str)
    
    # 定义正则表达式来匹配每一行
    row_pattern = re.compile(r'\|(\d+)\|([\d\.\-]+)\|([\d\.\-]+)\|(.+?)\|')
    
    # 存储表格的内容
    data = []
    
    # 查找所有匹配的行
    for match in row_pattern.finditer(markdown_str):
        index = match.group(1).strip()   # 行索引
        log_p = match.group(2).strip()   # Log(p) Per Token
        protrek_score = match.group(3).strip()  # Protrek Score
        protein_sequence = match.group(4).strip()  # Protein Sequence
        
        # 将一行数据添加到表格中
        data.append([index, log_p, protrek_score, protein_sequence])
    
    # 创建DataFrame
    df = pd.DataFrame(data, columns=['Index', 'Log(p) Per Token', 'Protrek Score', 'Protein Sequence'])
    
    return df

def dataframe_to_fasta(df, fasta_path):
    with open(fasta_path, 'w') as fasta_file:
        for index, row in df.iterrows():
            fasta_file.write(f">Design_{row['Index']} Log(p)_{row['Log(p) Per Token']} ProtrekScore_{row['Protrek Score']}\n")
            fasta_file.write(f"{row['Protein Sequence']}\n")
    print(f"FASTA file saved to {fasta_path}")

def run(input_text, design_num, save_dir):
    client = Client("http://www.denovo-pinal.com/")
    result = client.predict(
            input_text, design_num,
            api_name="/design_and_protrek_score"
    )
    markdown_result = result[0]
    df = markdown_to_dataframe(markdown_result)
    save_path = f"{save_dir}/pinal_results.csv"
    df.to_csv(save_path, index=False)
    dataframe_to_fasta(df, f"{save_dir}/designs.fasta")

def get_args():
    parser = argparse.ArgumentParser(description="Pinal De novo Protein Design")
    parser.add_argument("--input_text", type=str, required=True, help="The input text.")
    parser.add_argument("--design_num", type=int, required=True, help="The design number.")
    parser.add_argument("--save_dir", type=str, required=True, help="The directory to save the result.")
    return parser.parse_args()

def main(args):
    run(args.input_text, args.design_num, args.save_dir)
    
if __name__ == "__main__":
    """
    EXAMPLE:
    python cmd.py   --input_text "protein that has more than 2 loops" \
                    --design_num 5 \
                    --save_dir "./"
    """
    args = get_args()
    main(args)