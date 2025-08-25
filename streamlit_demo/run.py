import streamlit as st

pg = st.navigation(["pages/files.py", "pages/login.py", "pages/chat.py", "pages/user.py", "pages/tools.py", "pages/workflow.py"], position='hidden')
pg.run()
