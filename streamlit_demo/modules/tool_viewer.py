import streamlit as st
import os

from agent.tools.tool_manager import ToolManager
from streamlit_demo.backend.frontend_api import sync_toolset


@st.fragment
def show_available_tools():
    # Put each tool in its category
    category2tools = {}
    for name, obj in st.session_state.tool_manager.tools.items():
        doc_dict = obj.config.document
        if doc_dict.category_name == "chat":
            continue
        category2tools[doc_dict.category_name] = category2tools.get(doc_dict.category_name, []) + [doc_dict.tool_name]
    
    # sort dict
    for category in category2tools.keys():
        category2tools[category] = sorted(category2tools[category])
    
    sorted_cates = sorted(category2tools.keys())
    # List all available tools by category
    tabs = st.tabs(sorted_cates)
    
    for i, category in enumerate(sorted_cates):
        tools = category2tools[category]
        with tabs[i]:
            for name in tools:
                obj = st.session_state.tool_manager.get_tool(name)
                doc_dict = obj.config.document
                with st.expander(name):
                    st.markdown(f"*{doc_dict.tool_description}*")
                    # List all required arguments
                    if len(doc_dict.required_parameters) > 0:
                        st.markdown(f"**Required arguments**")
                        for arg_dict in doc_dict.required_parameters:
                            st.markdown(f"- **{arg_dict.name.strip()}**\n\n*{arg_dict.description.strip()}*")
            
                    # List all optional arguments
                    # try:
                    #     if len(doc_dict.optional_parameters) > 0:
                    #         st.markdown("**Optional arguments**")
                    #         for arg_dict in doc_dict.optional_parameters:
                    #             st.markdown(f"- **{arg_dict.name.strip()}**\n\n*{arg_dict.description.strip()}*")
                    # except Exception as e:
                    #     st.markdown(f"Error in tool {name}: {e}")
                    
                    if len(doc_dict.optional_parameters) > 0:
                            st.markdown("**Optional arguments**")
                            for arg_dict in doc_dict.optional_parameters:
                                st.markdown(f"- **{arg_dict.name.strip()}**\n\n*{arg_dict.description.strip()}*")

# @st.fragment
# def st_tool_viewer():
#     if st.button("View available tools", use_container_width=True):
#         show_available_tools()
    
    # if st.button("Sync toolset", use_container_width=True):
    #     # This may take a while
    #     st.session_state.is_syncing = True
    #     # disappear when done
    #     if st.session_state.is_syncing:
    #         st.markdown("Syncing toolset...")
        
    #     # Frontend
    #     del st.session_state.tool_manager
    #     st.session_state.tool_manager = ToolManager()
        
    #     # Backend
    #     result = sync_toolset(out_dir=st.session_state.out_dir)
    #     st.session_state.is_syncing = False
    #     if "error" in result:
    #         st.error(result["error"])
    #     else:
    #         st.success("Toolset synced successfully")
    #         st.markdown(result)
