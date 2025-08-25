import time
import streamlit as st
import json

@st.fragment
def st_plan_detail(plan_set, uid):
    if len(plan_set) == 1:
        plan_dict = plan_set[-1]
    else:
        plan_options = [f"Plan Round {i}" for i in range(len(plan_set), 0, -1)]
        
        selection = st.radio(label='plan round', options=plan_options, label_visibility="collapsed", horizontal=True, key=f"plan_round_selection_{uid}", disabled=st.session_state.get("is_chatting", False))

        
        plan_dict = plan_set[int(selection.split()[-1]) - 1]
    if plan_dict:
        st.markdown("### Plan")
    # st.write(plan_dict)
    user_request = plan_dict.get("user_request", "")
    user_request = "" if user_request is None else user_request
    analysis = plan_dict.get("analysis", "")
    analysis = "" if analysis is None else analysis
    st.write(user_request+" "+analysis)
    for step_id, step_dict in plan_dict.items():
        if not step_id.startswith("step_") or not step_dict:
            continue
        if step_dict.get("tool") is None or step_dict.get("tool") == "" or step_dict.get("tool") == "chat":
            continue
        else:
            if "running_log" not in step_dict:
                # initial icon
                execution_icon = ":material/circle:"
            elif "error" in step_dict:
                execution_icon = ":material/running_with_errors:"
            elif "results" not in step_dict:
                execution_icon = ":material/clock_loader_40:"
            else:
                execution_icon = ":material/check_circle:"
        
        idx = int(step_id.split("_")[-1])
        st.write(f"#### {execution_icon} Step {idx}: {step_dict.get('tool','')}")
        step_analysis = step_dict.get("analysis", "")
        step_analysis = "" if step_analysis is None else step_analysis
        step_reason = step_dict.get("reason", "")
        step_reason = "" if step_reason is None else step_reason
        step_thoughts = step_reason + " " + step_analysis
        st.write(step_thoughts)

        if "error" in step_dict:
            st.write(f"```\n{step_dict['error']}\n```")
        
        elif 'tool_arg' in step_dict:
            st.write(f"###### Arguments:")
            st.write(f"```python\n{json.dumps(step_dict.get('tool_arg', {}), indent=4)}\n```")
            
            # Display running log
            if "running_log" in step_dict:
                with st.expander(f"**Running log:**", expanded=True):
                    st.write(f"```\n{step_dict['running_log']}\n```")
                    css = '''
                    <style>
                        [data-testid="stExpander"] div:has(>.stCode) {
                            overflow: auto;
                            overflow-x: hidden;
                            max-height: 300px;
                        }
                    </style>
                    '''
                    st.markdown(css, unsafe_allow_html=True)
