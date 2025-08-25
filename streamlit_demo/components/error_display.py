import streamlit as st

def reset_error_display():
    st.session_state.error_display_time_limit = 6000
    st.session_state.error_display_now_time = st.session_state.error_display_time_limit

@st.fragment(run_every=1)
def display_timer():
    """
    Set a countdown timer
    """
    if st.session_state.error_display_now_time == 0:
        st.rerun()
    else:
        st.session_state.error_display_now_time -= 1
        percentage = int(st.session_state.error_display_now_time / st.session_state.error_display_time_limit * 100)

        st.markdown(f"Will refresh this page in <font color='red'>{st.session_state.error_display_now_time}</font> seconds",
                    unsafe_allow_html=True)
        st.progress(percentage)