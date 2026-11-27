

import streamlit as st

from wikipedia_extractor_core import (
    WikipediaExtractor,
    safe_filename,
    numbered_filename,
    format_txt,
)


st.set_page_config(page_title="Wikipedia Extractor", layout="wide")


DEFAULTS = {
    "topic": None,
    "article": None,
    "titles": [],
    "selected": [],
    "sections": [],
    "saved_path": None,
    "pending_overwrite": None,
    "pending_filename": None,
    "downloaded_filenames": [],
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = list(v) if isinstance(v, list) else v


if st.session_state.article is None and (
    st.session_state.titles or st.session_state.sections
):
    for k, v in DEFAULTS.items():
        st.session_state[k] = list(v) if isinstance(v, list) else v
    st.rerun()


with st.sidebar:
    st.header("Controls")
    if st.button("Start Over", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.caption("Clears everything and returns to the search step.")


st.title("Wikipedia Article Extractor")
with st.expander("How to use this app"):
    st.markdown(
        "1. Type a topic into the box and press **Search**.\n"
        "2. Pick one or more sections from the **multiselect**.\n"
        "3. Click **Extract** to preview the content.\n"
        "4. Click **Download .txt** to save it to your device."
    )


cols = st.columns(4)
steps = [
    ("Search",   bool(st.session_state.topic)),
    ("Select",   bool(st.session_state.titles)),
    ("Extract",  bool(st.session_state.sections)),
    ("Download", bool(st.session_state.downloaded_filenames)),
]
for col, (label, done) in zip(cols, steps):
    col.caption(("✅ " if done else "⬜ ") + label)

# 7. Stage 1 — Search form
with st.form("search_form"):
    topic_input = st.text_input("Enter a topic", value="")
    submitted = st.form_submit_button("Search")

if submitted:
    topic = topic_input.strip()
    if not topic:
        st.warning("Please type a topic first.")
    else:
        st.session_state.topic = topic
        with st.spinner("Fetching article..."):
            article = WikipediaExtractor()
            article.fetch(topic)

        if article.error:
            st.error(article.error)
            st.session_state.article = None
            st.session_state.titles = []
            st.session_state.selected = []
            st.session_state.sections = []
        else:
            st.session_state.article = article
            st.session_state.titles = article.list_top_sections()
            st.session_state.selected = []
            st.session_state.sections = []


if st.session_state.article is not None and st.session_state.article.error is None:
    st.success(f"Found: **{st.session_state.article.title}**")
    st.write(st.session_state.article.url)


if (
    st.session_state.article is not None
    and st.session_state.article.error is None
):
    if len(st.session_state.titles) <= 1:
        st.warning("This article has too few usable sections to extract.")
    else:
        selected = st.multiselect(
            "Select sections",
            options=st.session_state.titles,
            default=st.session_state.selected,
        )
        st.session_state.selected = selected

        # 10. Stage 3 — Extract
        if st.button("Extract"):
            if not selected:
                st.warning("Please select at least one section.")
            else:
                extracted = []
                for t in selected:
                    text = st.session_state.article.extract_section(t)
                    if text:
                        extracted.append(text)
                if not extracted:
                    st.warning("No content could be extracted from the selected sections.")
                else:
                    st.session_state.sections = extracted


if st.session_state.sections and st.session_state.article is not None:
    with st.container(border=True):
        for sec_text in st.session_state.sections:
            lines = sec_text.strip("\n").split("\n")
            header = lines[0].strip("= ").strip() if lines else "Section"
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""
            st.subheader(header)
            st.text(body)

    article = st.session_state.article
    content = format_txt(article.title, article.url, st.session_state.sections)
    base = safe_filename(article.title)
    proposed = base + ".txt"

    
    if proposed in st.session_state.downloaded_filenames:
        st.warning(
            f"You already downloaded a file named `{proposed}` in this session. "
            f"Downloading again will add a `(2)` suffix."
        )

    unique_name = numbered_filename(base, st.session_state.downloaded_filenames)

    # 將字串轉做 bytes，強制 Browser 乖乖聽話
    file_data = content.encode("utf-8")
    base = safe_filename(article.title)
    unique_name = numbered_filename(base, st.session_state.downloaded_filenames)

    # 撞名警告
    if proposed in st.session_state.downloaded_filenames:
        st.warning(
            f"You already downloaded a file named `{proposed}` in this session. "
            f"Downloading again will add a `_v2` suffix."
        )

    # 💡 呢個係關鍵：用 callback function 去記錄，唔好用 st.rerun()
    def add_downloaded(filename):
        st.session_state.downloaded_filenames.append(filename)

    st.download_button(
        label="Download .txt",
        data=file_data,
        file_name=unique_name,
        mime="text/plain",
        key="download_btn",
        on_click=add_downloaded,   # 👈 撳完之後喺後台默默記錄
        args=(unique_name,)
    )



st.caption("Content from Wikipedia, CC BY-SA 4.0.")
st.write(st.session_state)