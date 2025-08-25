import streamlit as st

def add_new_item():
    """Add new empty item to the items list"""
    st.session_state.added_args.append({
        'name': '',
        'description': '',
        'deleted': False,
        'type': ''  # 初始化type字段
    })

def delete_item(original_index):
    """Mark item at specified original index as deleted"""
    if 0 <= original_index < len(st.session_state.added_args):
        st.session_state.added_args[original_index]['deleted'] = True

def render_arguments():
    """Render all form elements dynamically"""
    # 保留原始索引
    filtered_items_with_indices = [
        (original_idx, item) 
        for original_idx, item in enumerate(st.session_state.added_args)
        if not item.get('deleted', False)
    ]
    
    for original_idx, item in filtered_items_with_indices:
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.subheader(f"Argument {original_idx + 1}")  # 使用原始索引显示
        
        with col2:
            # Argument Name input
            name = st.text_input("Argument Name", 
                                value=item['name'], 
                                key=f"name_{original_idx}")
            item['name'] = name
            
            # Argument Type selectbox
            type_options = [  
                'SEQUENCE', 'MOLECULE', 'PATH', 'SELECTION', 'DATE',
                'INTEGER', 'FLOAT', 'BOOLEAN', 'TEXT', 'DICT',
                'LIST', 'UNIPROT_ID', 'PDB_ID', 'PFAM_ID'
            ]
            # 处理type字段缺失的情况
            current_type = item.get('type', '')
            try:
                default_index = type_options.index(current_type)
            except ValueError:
                default_index = 0  # 默认选第一个选项
            
            selected_type = st.selectbox(
                "Argument Type",
                type_options,
                index=default_index,
                key=f"type_{original_idx}"
            )
            item['type'] = selected_type
            
            # Argument Description text area
            description = st.text_area("Argument Description", 
                                      value=item['description'],
                                      key=f"desc_{original_idx}")
            item['description'] = description
            
        # 使用原始索引作为键和参数
        if st.button("Delete", 
                    key=f"delete_{original_idx}",
                    on_click=lambda idx=original_idx: delete_item(idx)):
            pass

@st.dialog("Add New Tool", width="large")
def add_new_tool():
    # Clear and start
    if 'added_args' not in st.session_state:
        st.session_state.added_args = []
    
    st.write("### Basic Information")
    tool_name = st.text_input("Tool Name")
    tool_description = st.text_area("Tool Description")
    tool_category = st.selectbox("Tool Category", 
                                ["Design", "Function", "Knowledge", 
                                 "Multimodel", "Sequence", "Structure", "Other"])
    
    st.write("### Arguments")
    if st.button(label="Add arguments",icon=":material/add:"):
        add_new_item()
    
    render_arguments()
    
    submitted = st.button("Submit")
    if submitted:
        st.session_state.added_tool = {
            'name': tool_name,
            'description': tool_description,
            'category': tool_category,
            'args': [item for item in st.session_state.added_args 
                    if not item.get('deleted', False)]
        }
        st.rerun()