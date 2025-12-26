import json
import random
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="MOCLAM Quiz", layout="centered")

BASE_DIR = Path(__file__).parent
DATA_SOURCES = {
    "Preguntas generadas": BASE_DIR / "data",
    "Preguntas libro": BASE_DIR / "data2",
}

def load_questions(chapter: int, data_dir: Path):
    path = data_dir / f"capitulo_{chapter}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------------
# Session state defaults
# -------------------------
if "chapter" not in st.session_state:
    st.session_state.chapter = 1
if "mode" not in st.session_state:
    st.session_state.mode = "Práctica"
if "questions" not in st.session_state:
    st.session_state.questions = []
if "idx" not in st.session_state:
    st.session_state.idx = 0

if "data_source_label" not in st.session_state:
    st.session_state.data_source_label = "Preguntas generadas"
if "load_error" not in st.session_state:
    st.session_state.load_error = None

if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}  # {qkey: "A"/"B"/"C"}

if "active_qkey" not in st.session_state:
    st.session_state.active_qkey = None

# radio estable
if "current_choice" not in st.session_state:
    st.session_state.current_choice = "A"

# feedback
if "answered" not in st.session_state:
    st.session_state.answered = False
if "last_correct" not in st.session_state:
    st.session_state.last_correct = None

# -------------------------
# Sidebar
# -------------------------
st.sidebar.title("📘 MOCLAM Quiz")

source_options = list(DATA_SOURCES.keys())
source_index = source_options.index(st.session_state.data_source_label) if st.session_state.data_source_label in DATA_SOURCES else 0
data_source_label = st.sidebar.radio(
    "Banco de preguntas",
    source_options,
    index=source_index
)

chapter = st.sidebar.selectbox(
    "Capítulo",
    list(range(1, 10)),
    index=st.session_state.chapter - 1
)

mode = st.sidebar.radio(
    "Modo",
    ["Práctica", "Simulacro"],
    index=0 if st.session_state.mode == "Práctica" else 1
)

order_mode = st.sidebar.radio(
    "Orden de preguntas",
    ["En orden", "Aleatorias"]
)

nq = st.sidebar.slider(
    "Cantidad de preguntas",
    min_value=5,
    max_value=30,
    value=30,
    step=1
)

# Recomendado: evita saltos accidentales
lock_next_until_answer = st.sidebar.toggle(
    "Bloquear “Siguiente” hasta responder",
    value=True
)

if st.sidebar.button("Comenzar / Reiniciar", key="btn_start"):
    st.session_state.chapter = chapter
    st.session_state.mode = mode
    st.session_state.data_source_label = data_source_label
    st.session_state.load_error = None

    st.session_state.user_answers = {}
    st.session_state.active_qkey = None
    st.session_state.current_choice = "A"
    st.session_state.answered = False
    st.session_state.last_correct = None

    data_dir = DATA_SOURCES[data_source_label]
    try:
        qs = load_questions(chapter, data_dir)  # en orden del JSON
    except FileNotFoundError:
        st.session_state.questions = []
        st.session_state.idx = 0
        st.session_state.load_error = f"No se encontro capitulo_{chapter}.json en {data_dir.name}."
    else:
        if order_mode == "Aleatorias":
            random.shuffle(qs)

        st.session_state.questions = qs[:min(nq, len(qs))]
        st.session_state.idx = 0

# -------------------------
# Main
# -------------------------
st.title("MOCLAM – De Creación a Nueva Creación")
st.caption("Quiz de alternativas (A/B/C).")

if not st.session_state.questions:
    if st.session_state.load_error:
        st.error(st.session_state.load_error)
        st.stop()
    st.info("Elige capítulo y presiona **Comenzar / Reiniciar**.")
    st.stop()

total = len(st.session_state.questions)

# -------------------------
# Callbacks (evitan “acciones cruzadas” en responsive)
# -------------------------
def go_prev():
    if st.session_state.idx > 0:
        st.session_state.idx -= 1
        st.session_state.answered = False
        st.session_state.last_correct = None
        st.session_state.active_qkey = None  # fuerza recarga estado pregunta

def go_next():
    if st.session_state.idx < total:
        st.session_state.idx += 1
        st.session_state.answered = False
        st.session_state.last_correct = None
        st.session_state.active_qkey = None

def answer_current(qkey: str, correct_answer: str):
    # IMPORTANTE: aquí NO se mueve idx (no avanza)
    st.session_state.user_answers[qkey] = st.session_state.current_choice
    st.session_state.answered = True
    st.session_state.last_correct = (st.session_state.current_choice == correct_answer)

# -------------------------
# Finished
# -------------------------
if st.session_state.idx >= total:
    score = 0
    for qq in st.session_state.questions:
        qk = f"{st.session_state.chapter}-{qq['id']}"
        if st.session_state.user_answers.get(qk) == qq["answer"]:
            score += 1

    st.success(f"✅ Terminaste. Puntaje: {score} / {total}")

    if st.session_state.mode == "Simulacro":
        wrong = []
        for qq in st.session_state.questions:
            qk = f"{st.session_state.chapter}-{qq['id']}"
            ch = st.session_state.user_answers.get(qk)
            if ch and ch != qq["answer"]:
                wrong.append((qq, ch))

        if wrong:
            st.subheader("❌ Preguntas incorrectas")
            for qq, ch in wrong:
                st.markdown(f"**{qq['id']}. {qq['question']}**")
                st.write(f"Tu respuesta: **{ch}** — Correcta: **{qq['answer']}**")
                st.write(f"A) {qq['options']['A']}")
                st.write(f"B) {qq['options']['B']}")
                st.write(f"C) {qq['options']['C']}")
                st.divider()

    st.stop()

# -------------------------
# Current question
# -------------------------
q = st.session_state.questions[st.session_state.idx]
qkey = f"{st.session_state.chapter}-{q['id']}"

# Si cambiaste de pregunta, recarga estado desde user_answers
if st.session_state.active_qkey != qkey:
    st.session_state.active_qkey = qkey
    st.session_state.current_choice = st.session_state.user_answers.get(qkey, "A")
    st.session_state.answered = (qkey in st.session_state.user_answers)
    st.session_state.last_correct = None  # no dispara feedback al navegar

st.markdown(f"### Capítulo {st.session_state.chapter} · Pregunta {st.session_state.idx + 1} de {total}")
st.progress((st.session_state.idx + 1) / total)

# Puntaje live
live_score = 0
answered_count = 0
for qq in st.session_state.questions:
    qk = f"{st.session_state.chapter}-{qq['id']}"
    if qk in st.session_state.user_answers:
        answered_count += 1
    if st.session_state.user_answers.get(qk) == qq["answer"]:
        live_score += 1
st.caption(f"Respondidas: {answered_count}/{total} · Puntaje: {live_score}")

st.write(q["question"])

st.radio(
    "Selecciona una alternativa:",
    ["A", "B", "C"],
    key="current_choice",
    format_func=lambda x: f"{x}) {q['options'][x]}",
)

# -------------------------
# Buttons (con callbacks + keys fijas)
# -------------------------
c1, c2, c3 = st.columns(3)

with c1:
    st.button(
        "⬅️ Anterior",
        key="btn_prev",
        use_container_width=True,
        disabled=(st.session_state.idx == 0),
        on_click=go_prev
    )

with c2:
    st.button(
        "Responder",
        key="btn_answer",
        use_container_width=True,
        on_click=answer_current,
        kwargs={"qkey": qkey, "correct_answer": q["answer"]}
    )

with c3:
    st.button(
        "Siguiente ➡️",
        key="btn_next",
        use_container_width=True,
        disabled=(lock_next_until_answer and (qkey not in st.session_state.user_answers)),
        on_click=go_next
    )

# -------------------------
# Feedback (solo práctica)
# -------------------------
if st.session_state.mode == "Práctica" and (qkey in st.session_state.user_answers):
    chosen = st.session_state.user_answers.get(qkey)

    st.divider()
    st.subheader("Resultado")

    st.write(f"✅ **Respuesta correcta:** {q['answer']}")
    st.write(f"📝 **Tu respuesta:** {chosen}")

    for opt in ["A", "B", "C"]:
        text = f"{opt}) {q['options'][opt]}"
        if opt == q["answer"]:
            st.success(text)
        elif chosen is not None and opt == chosen and chosen != q["answer"]:
            st.error(text)
        else:
            st.write(text)
