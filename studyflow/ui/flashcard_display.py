import random
import uuid
from datetime import datetime, timezone

import streamlit as st


SYSTEM_MESSAGE = "You are a flashcard writer for middle and high school students. Return only valid JSON."
TARGET_CARDS = 12
MIN_CARDS = 4
MAX_CARDS = 20
MAX_NOTES_CHARACTERS = 8000
OLD_FORMAT_KEYS = ("assignment", "priority", "known")


# ============================================================
# PROMPTS
# ============================================================

def _student_line(profile):
    profile = profile or {}
    region = profile.get("region") or "Virginia"
    grade = f"{profile['grade']} grade" if profile.get("grade") else "high school"
    school = f" at {profile['school']}" if profile.get("school") else ""
    return f"{grade}{school}, {region}", region


def _rules(region, count):
    return f"""Rules:
- Make exactly {count} cards.
- If source material is given (an assignment sheet, notes, or a photo), build the cards from it first and only fill gaps with closely related ideas.
- Match the {region} standards for this course and grade level (for Virginia, the Virginia SOL).
- If a unit, chapter, or list is named, only use that.
- Keep the front short: a term, a name, a date, or a short question.
- Keep the back to one or two clear sentences, under 30 words.
- For vocabulary in another language, put the word on the front and the English meaning on the back.
- For math or science, a front can be a short problem or rule name, with the answer or rule on the back.
- No duplicate cards and no trick questions.
- The title is a short name for the set, under 6 words.

Return only JSON in this format:
{{"title": "...", "cards": [{{"front": "...", "back": "..."}}]}}"""


def flashcard_prompt(assignment, profile):
    student, region = _student_line(profile)
    material = assignment.get("study_material") or ""
    return f"""Make study flashcards for this assignment.

Assignment: {assignment.get("name") or "Untitled"}
Type: {assignment.get("type") or "assignment"}
Course: {assignment.get("course") or "unknown"}
Details from the student: {assignment.get("description") or "none"}
From the assignment sheet: {material or "nothing extra"}
Student: {student}

{_rules(region, TARGET_CARDS)}"""


def request_prompt(request, course, count, profile, notes="", has_image=False):
    student, region = _student_line(profile)
    sources = []
    if notes:
        sources.append(f'The student uploaded these notes:\n"""\n{notes[:MAX_NOTES_CHARACTERS]}\n"""')
    if has_image:
        sources.append("The attached image is the student's notes, study guide, or worksheet. Use it.")
    source = "\n\n".join(sources) or "No notes were uploaded."
    return f"""Make study flashcards for this request.

What the student wants: {request or "flashcards from the attached notes"}
Course: {course or "not given"}
Student: {student}

{source}

{_rules(region, clamp_count(count))}"""


def clamp_count(count):
    try:
        return min(MAX_CARDS, max(5, int(count)))
    except (TypeError, ValueError):
        return TARGET_CARDS


# ============================================================
# MAKING CARDS
# ============================================================

def _text(value):
    return " ".join(str(value or "").split())


def _card(front, back, known=False):
    front = _text(front)
    back = _text(back)
    if not front or not back:
        return None
    return {"front": front, "back": back, "known": bool(known)}


def _unique(cards):
    seen = set()
    unique = []
    for card in cards:
        if card and card["front"].lower() not in seen:
            seen.add(card["front"].lower())
            unique.append(card)
    return unique[:MAX_CARDS]


def clean_cards(result):
    if not isinstance(result, dict) or not isinstance(result.get("cards"), list):
        return []
    cards = []
    for item in result["cards"]:
        if isinstance(item, dict):
            cards.append(_card(
                item.get("front") or item.get("term") or item.get("question"),
                item.get("back") or item.get("definition") or item.get("answer")
            ))
    return _unique(cards)


def set_title(result, fallback):
    title = _text(result.get("title")) if isinstance(result, dict) else ""
    words = title.split()
    if not words:
        words = _text(fallback).split()[:6]
    return " ".join(words[:8]) or "Flashcards"


def new_set(title, course, cards, source="assignment"):
    return {
        "id": uuid.uuid4().hex,
        "assignment": _text(title) or "Flashcards",
        "course": _text(course),
        "source": source,
        "created": datetime.now(timezone.utc).isoformat(),
        "cards": cards
    }


def _same_assignment(card_set, assignment):
    return (
        card_set.get("source", "assignment") == "assignment"
        and card_set.get("assignment", "").lower() == _text(assignment.get("name")).lower()
        and card_set.get("course", "").lower() == _text(assignment.get("course")).lower()
    )


def find_set(sets, assignment):
    for index, card_set in enumerate(sets or []):
        if _same_assignment(card_set, assignment):
            return index
    return None


def _from_old_format(item):
    known = item.get("known") if isinstance(item.get("known"), dict) else {}
    cards = [
        _card(front, back)
        for front, back in item.items()
        if front not in OLD_FORMAT_KEYS and isinstance(back, str)
    ]
    cards += [_card(front, back, True) for front, back in known.items() if isinstance(back, str)]
    return cards


def normalize_sets(sets):
    normalized = []
    for item in sets or []:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("cards"), list):
            cards = [
                _card(card.get("front"), card.get("back"), card.get("known"))
                for card in item["cards"]
                if isinstance(card, dict)
            ]
        else:
            cards = _from_old_format(item)
        cards = _unique(cards)
        if not cards:
            continue
        normalized.append({
            "id": str(item.get("id") or uuid.uuid4().hex),
            "assignment": _text(item.get("assignment")) or "Flashcards",
            "course": _text(item.get("course")),
            "source": "request" if item.get("source") == "request" else "assignment",
            "created": str(item.get("created") or ""),
            "cards": cards
        })
    return normalized


def known_count(card_set):
    return sum(1 for card in card_set["cards"] if card["known"])


# ============================================================
# PRACTICE STATE
# ============================================================

def _state_key(card_set):
    return f"fc_state_{card_set['id']}"


def _order(card_set, mode):
    cards = card_set["cards"]
    if mode == "learning":
        return [index for index, card in enumerate(cards) if not card["known"]]
    return list(range(len(cards)))


def _state(card_set):
    key = _state_key(card_set)
    state = st.session_state.get(key)
    if not state or any(index >= len(card_set["cards"]) for index in state["order"]):
        state = {"order": _order(card_set, "all"), "pos": 0, "flipped": False, "mode": "all", "round_known": 0}
        st.session_state[key] = state
    return state


def reset_state(card_set):
    st.session_state.pop(_state_key(card_set), None)


def _start(card_set, mode, shuffle=False):
    order = _order(card_set, mode)
    if shuffle:
        random.shuffle(order)
    st.session_state[_state_key(card_set)] = {
        "order": order, "pos": 0, "flipped": False, "mode": mode, "round_known": 0
    }


def _flip(card_set):
    state = _state(card_set)
    state["flipped"] = not state["flipped"]


def _move(card_set, step):
    state = _state(card_set)
    state["pos"] = min(max(state["pos"] + step, 0), len(state["order"]))
    state["flipped"] = False


def _mark(card_set, knew_it, save):
    state = _state(card_set)
    if state["pos"] >= len(state["order"]):
        return
    card_set["cards"][state["order"][state["pos"]]]["known"] = knew_it
    if knew_it:
        state["round_known"] += 1
    state["pos"] += 1
    state["flipped"] = False
    save()


def _change_mode(card_set):
    key = f"fc_mode_{card_set['id']}"
    if not st.session_state.get(key):
        st.session_state[key] = "All cards"
    _start(card_set, "learning" if st.session_state[key] == "Still learning" else "all")


def _forget_all(card_set, save):
    for card in card_set["cards"]:
        card["known"] = False
    _start(card_set, "all")
    st.session_state[f"fc_mode_{card_set['id']}"] = "All cards"
    save()


# ============================================================
# STUDY VIEW
# ============================================================

def _finished(card_set, state, save):
    total = len(card_set["cards"])
    known = known_count(card_set)
    learning = total - known
    reviewed = len(state["order"])

    if reviewed:
        st.success(
            f"Round done! You knew {state['round_known']} of {reviewed} "
            f"card{'s' if reviewed != 1 else ''} this time.",
            icon=":material/task_alt:"
        )
    else:
        st.success("You know every card in this set.", icon=":material/task_alt:")

    st.caption(f"{known} of {total} known overall · {learning} still learning")

    again_column, all_column = st.columns(2)
    with again_column:
        if learning:
            st.button(
                f":material/replay: Practice the {learning} I'm still learning",
                key=f"fc_again_{card_set['id']}",
                type="primary",
                width="stretch",
                on_click=_start,
                args=(card_set, "learning", True)
            )
    with all_column:
        st.button(
            ":material/restart_alt: Go through all cards",
            key=f"fc_all_{card_set['id']}",
            width="stretch",
            on_click=_start,
            args=(card_set, "all")
        )


def show_set(card_set, save, delete):
    set_id = card_set["id"]
    cards = card_set["cards"]
    total = len(cards)
    known = known_count(card_set)
    state = _state(card_set)

    st.progress(known / total if total else 0, text=f"{known} of {total} known")

    if f"fc_mode_{set_id}" not in st.session_state:
        st.session_state[f"fc_mode_{set_id}"] = "Still learning" if state["mode"] == "learning" else "All cards"
    st.segmented_control(
        "Practice",
        ["All cards", "Still learning"],
        key=f"fc_mode_{set_id}",
        on_change=_change_mode,
        args=(card_set,),
        label_visibility="collapsed"
    )

    if state["pos"] >= len(state["order"]):
        _finished(card_set, state, save)
    else:
        card = cards[state["order"][state["pos"]]]
        side = "back" if state["flipped"] else "front"
        st.caption(
            f"Card {state['pos'] + 1} of {len(state['order'])} · "
            f"{'Answer' if state['flipped'] else 'Question'} · Tap the card to flip it"
        )
        st.button(
            card[side],
            key=f"fc_card_{set_id}_{side}",
            width="stretch",
            on_click=_flip,
            args=(card_set,)
        )

        with st.container(key=f"fc_controls_{set_id}"):
            back_column, still_column, got_column, next_column = st.columns([1, 3, 3, 1])
            with back_column:
                st.button(
                    ":material/chevron_left:",
                    key=f"fc_prev_{set_id}",
                    help="Previous card",
                    type="tertiary",
                    disabled=state["pos"] == 0,
                    width="stretch",
                    on_click=_move,
                    args=(card_set, -1)
                )
            with still_column:
                st.button(
                    ":material/close: Still learning",
                    key=f"fc_still_{set_id}",
                    width="stretch",
                    on_click=_mark,
                    args=(card_set, False, save)
                )
            with got_column:
                st.button(
                    ":material/check: Got it",
                    key=f"fc_got_{set_id}",
                    type="primary",
                    width="stretch",
                    on_click=_mark,
                    args=(card_set, True, save)
                )
            with next_column:
                st.button(
                    ":material/chevron_right:",
                    key=f"fc_next_{set_id}",
                    help="Skip this card",
                    type="tertiary",
                    width="stretch",
                    on_click=_move,
                    args=(card_set, 1)
                )

    with st.container(key=f"fc_tools_{set_id}"):
        shuffle_column, reset_column, delete_column = st.columns(3)
        with shuffle_column:
            st.button(
                ":material/shuffle: Shuffle",
                key=f"fc_shuffle_{set_id}",
                type="tertiary",
                width="stretch",
                on_click=_start,
                args=(card_set, state["mode"], True)
            )
        with reset_column:
            st.button(
                ":material/restart_alt: Reset",
                key=f"fc_reset_{set_id}",
                type="tertiary",
                width="stretch",
                on_click=_forget_all,
                args=(card_set, save)
            )
        with delete_column:
            with st.popover(":material/delete: Delete", width="stretch"):
                st.write(f"Delete all {total} cards for **{card_set['assignment']}**?")
                st.button(
                    "Yes, delete",
                    key=f"fc_delete_{set_id}",
                    type="primary",
                    width="stretch",
                    on_click=delete,
                    args=(set_id,)
                )
