import streamlit as st
def draw(side, top, bottom, set_idx):
    if st.button(
        top if side == 0 else bottom,
        width='stretch',
        type='tertiary',
        key=f'flashcard_{set_idx}',
    ):
        return 1 if side == 0 else 0
    else:
        return side