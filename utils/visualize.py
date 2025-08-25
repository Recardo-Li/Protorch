import os
import py3Dmol
import re


def visualize(structure_path: str) -> dict:
    """
    Visualize a structure file.

    Args:
        structure_path (str): Path to the pdb file.
    
    Returns:
        A dict of html code for visualization.
            html: The visualized html file path.
    """
    assert os.path.exists(structure_path), f"Error: {structure_path} does not exist!"
    

    file_type = str(structure_path).split(".")[-1]
    if file_type == "cif":
        file_type == "mmcif"

    view = py3Dmol.view(js='https://3dmol.org/build/3Dmol.js',)
    view.addModel(open(structure_path,'r').read(),file_type)

    view.setStyle({'cartoon': {'color':'spectrum'}})

    output_path = f"outputs/{structure_path.split('/')[-1].split('.')[0]}.html"
    view.zoomTo()
    # 获取生成的 HTML 内容
    html_content = view._make_html()
    html_content_modified = re.sub(
        r'(<div id="3dmolviewer_\d+"  style=")[^"]*(">)',
        r'\1position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;\2',
        html_content
    )
    # 将修改后的 HTML 内容写入文件
    with open(output_path, 'w') as f:
        f.write(html_content_modified)
    return output_path




