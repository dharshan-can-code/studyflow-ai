import streamlit as st
def draw(side, top, bottom):
    if st.button(
        top if side == 0 else bottom,
        width='stretch',
        type='tertiary',
        key='flashcard',
    ):
        return 1 if side == 0 else 0
    else:
        return side