import streamlit as st


def hide_running_man():
    """
    Hide the animation of a running man on top of the Streamlit app.
    """
    hide_streamlit_style = """
                    <style>
                    div[data-testid="stStatusWidget"] {
                    visibility: hidden;
                    height: 0%;
                    position: fixed;
                    }
                    </style>
                    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
