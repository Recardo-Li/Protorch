import os
import os.path
import urllib
import streamlit as st
import numpy as np
import time
import streamlit.components.v1 as components

from urllib.parse import urljoin
from html import escape
from base64 import b64encode
from functools import partial
from filetype import image_match, video_match, audio_match
from streamlit_ace import st_ace
from streamlit_molstar import st_molstar, st_molstar_remote
from streamlit_molstar.auto import st_molstar_auto
from streamlit_embeded import st_embeded


def _do_fasta_preview(abs_path, key="fasta-preview"):
    with open(abs_path) as r:
        content = r.readlines(10000)
        if len(content) == 10000:
            st.warning("The file is too large. Only the first 10000 lines are displayed.")
        st_ace(value="".join(content), readonly=True, show_gutter=False, height=300, key=key)


def _do_code_preview(abs_path, key="code-preview", **kwargs):
    with open(abs_path) as f:
        st.code(f.read(), key=key, **kwargs)


def _do_pdf_preview(abs_path, url=None, height="420px", key="pdf-preview"):
    if url:
        safe_url = escape(url)
    else:
        with open(abs_path, "rb") as f:
            data = b64encode(f.read()).decode("utf-8")
        safe_url = f"data:application/pdf;base64,{data}"
    pdf_display = f'<iframe src="{safe_url}" width="100%" min-height="240px" height="{height} type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True, key=key)


def _do_molecule_preview(abs_path, url=None, key="molecule-preview", **kwargs):
    use_auto = kwargs.pop("use_auto", False)
    test_traj_path = os.path.splitext(abs_path)[0] + ".xtc"
    if os.path.exists(test_traj_path):
        traj_path = test_traj_path
        traj_url = os.path.splitext(url)[0] + ".xtc" if url else None
    else:
        traj_path = None
        traj_url = None
    if use_auto:
        st_molstar_auto(
            [{"file": url, "local": abs_path} if url else abs_path], key=key, **kwargs
        )
    else:
        if url:
            st_molstar_remote(url, traj_url, key=key, **kwargs)
        else:
            st_molstar(abs_path, traj_path, key=key, **kwargs)
    return True


def _do_csv_preview(abs_path, key="csv-preview", **kwargs):
    import pandas as pd

    df = pd.read_csv(abs_path)
    mask = df.applymap(type) != bool
    d = {True: "True", False: "False"}
    df = df.where(mask, df.replace(d))
    df = df.replace(np.nan, None)
    st.dataframe(df, key=key, **kwargs)
    return True


def _do_tsv_preview(abs_path, key="tsv-preview", **kwargs):
    import pandas as pd

    df = pd.read_table(abs_path)
    mask = df.applymap(type) != bool
    d = {True: "True", False: "False"}
    df = df.where(mask, df.replace(d))
    df = df.replace(np.nan, None)
    st.dataframe(df, key=key, **kwargs)
    return True


def _do_json_preview(abs_path, key="json-preview", **kwargs):
    with open(abs_path) as f:
        st.json(f.read(), **kwargs)


def _do_html_preview(abs_path, url=None, key="html-preview", **kwargs):
    with open(abs_path) as f:
        html = f.read()
        file_path = os.path.basename(abs_path)

        artifacts_url = urljoin("https://launching.mlops.dp.tech/artifacts/", file_path[: file_path.rfind("/")+1])
        print(f"artifacts_url old: {artifacts_url}")
        artifacts_url = url[: url.rfind("/")+1]
        print(f"artifacts_url: {artifacts_url}")
        artifacts_url = artifacts_url.replace("https://launching.mlops.dp.tech/users/", "https://launching.mlops.dp.tech/artifacts/users/")
        artifacts_url = artifacts_url.replace("https://canary-launching.mlops.dp.tech/users/", "https://canary-launching.mlops.dp.tech/artifacts/users/")
        html = html.replace("launching-artifacts://", artifacts_url)
        st_embeded(html, key=key, **kwargs)
    return True


def _do_markdown_preview(abs_path, key="markdown-preview", **kwargs):
    with open(abs_path) as f:
        key = f'{kwargs.get("key", abs_path)}-preview'
        st.markdown(f.read(), key=key, unsafe_allow_html=True)


def _do_plain_preview(abs_path, key="plain-preview", **kwargs):
    with open(abs_path) as f:
        st_ace(value=f.read(), readonly=True, show_gutter=False, key=key)


# RNA Secondary Structure Formats
# DB (dot bracket) format (.db, .dbn) is a plain text format that can encode secondory structure.
def _do_dbn_preview(abs_path, key="dbn-preview"):
    with open(abs_path, "r", encoding="utf8") as f:
        content = f.read()

    encoding = urllib.parse.urlencode(
        {"id": "fasta", "file": content}, safe=r"()[]{}>#"
    )
    encoding = encoding.replace("%0A", "%5Cn").replace("#", ">")
    url = r"https://mrna-proxy.mlops.dp.tech/forna/forna.html?" + encoding
    components.iframe(url, height=600)


PREVIEW_HANDLERS = {
    extention: handler
    for extentions, handler in [
        (
            (
                ".pdb",
                ".pdbqt",
                ".ent",
                ".trr",
                ".nctraj",
                ".nc",
                ".ply",
                ".bcif",
                ".sdf",
                ".cif",
                ".mol",
                ".mol2",
                ".xyz",
                ".sd",
                ".gro",
                ".mrc",
            ),
            _do_molecule_preview,
        ),
        ((".mrc",), partial(_do_molecule_preview, use_auto=True)),
        ((".json",), _do_json_preview),
        ((".pdf",), _do_pdf_preview),
        ((".csv",), _do_csv_preview),
        ((".tsv",), _do_tsv_preview),
        ((".log", ".txt", ".md", ".upf", ".UPF", ".orb"), _do_plain_preview),
        ((".md",), _do_markdown_preview),
        ((".py", ".sh"), _do_code_preview),
        ((".html", ".htm"), _do_html_preview),
        ((".dbn",), _do_dbn_preview),
        ((".fasta",), _do_fasta_preview),
    ]
    for extention in extentions
}


@st.dialog("File preview")
def dialog_file_preview(path: str, **kwargs):
    """
    Show preview of a file
    Args:
        path: File path
    """
    file_name = os.path.basename(path)
    preview, raw = st.tabs(["Preview", "Raw"])

    # Preview a file based on its extension
    with preview:
        ext = os.path.splitext(path)[-1]
        if ext in PREVIEW_HANDLERS:
            try:
                handler = PREVIEW_HANDLERS[ext]
                handler(path, **kwargs)
            except Exception:
                st.error(f"Failed to preview {file_name}")

        # If the file is an image
        elif image_match(path):
            st.image(path, **kwargs)

        # If the file is a video
        elif ft := video_match(path):
            st.video(path, format=ft.mime, **kwargs)

        # If the file is an audio
        elif ft := audio_match(path):
            st.audio(path, format=ft.mime, **kwargs)

        # Display an error message
        else:
            st.info(f"Preview for {ext} is not supported. You can view the raw content instead.")

    # Display the raw text of the file
    with raw:
        try:
            with open(path) as r:
                content = r.readlines(10000)
                if len(content) == 10000:
                    st.warning("The file is too large. Only the first 10000 lines are displayed.")
                st_ace(value="".join(content), readonly=True, show_gutter=False, height=300, key=f"raw-{path}")

        except Exception:
            st.error(f"Failed to read {file_name}")


def file_preview(path: str, **kwargs):
    """
    Show preview of a file
    Args:
        path: File path
    """
    file_name = os.path.basename(path)
    preview, raw = st.tabs(["Preview", "Raw"])

    # Preview a file based on its extension
    with preview:
        ext = os.path.splitext(path)[-1]
        if ext in PREVIEW_HANDLERS:
            try:
                handler = PREVIEW_HANDLERS[ext]
                handler(path, key=f"{time.time()}", **kwargs)
            except Exception:
                st.error(f"Failed to preview {file_name}")

        # If the file is an image
        elif image_match(path):
            st.image(path, **kwargs)

        # If the file is a video
        elif ft := video_match(path):
            st.video(path, format=ft.mime, **kwargs)

        # If the file is an audio
        elif ft := audio_match(path):
            st.audio(path, format=ft.mime, **kwargs)

        # Display an error message
        else:
            st.info(f"Preview for {ext} is not supported. You can view the raw content instead.")

    # Display the raw text of the file
    with raw:
        try:
            with open(path) as r:
                content = r.readlines(10000)
                if len(content) == 10000:
                    st.warning("The file is too large. Only the first 10000 lines are displayed.")
                st_ace(value="".join(content), readonly=True, show_gutter=False, height=300, key=f"raw-{path}")

        except Exception:
            st.error(f"Failed to read {file_name}")