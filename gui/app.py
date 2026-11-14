import os
import queue
import threading

import customtkinter as ctk

from config import DOCS_DIR, WATCH_INTERVAL_MS
from gui import chat_view, theme
from services.rag import answer_question
from services.vector_store import folder_snapshot, sync_documents


def run_in_background(job, results, tag):
    """Run job() in a thread and drop (tag, result, error) into the queue."""
    def worker():
        try:
            results.put((tag, job(), None))
        except Exception as error:
            results.put((tag, None, error))

    threading.Thread(target=worker, daemon=True).start()


def build_header(window, on_pin_toggle):
    header = ctk.CTkFrame(window, fg_color=theme.HEADER_BG, corner_radius=0, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left", padx=18)

    title = ctk.CTkLabel(title_box, text="QueryBuddy", font=theme.FONT_TITLE,
                         text_color=theme.BUDDY_TEXT)
    title.pack(anchor="w", pady=(10, 0))

    status_row = ctk.CTkFrame(title_box, fg_color="transparent")
    status_row.pack(anchor="w")
    dot = ctk.CTkLabel(status_row, text="●", font=theme.FONT_SMALL,
                       text_color=theme.STATUS_BUSY, width=14)
    dot.pack(side="left")
    status = ctk.CTkLabel(status_row, text="Starting...", font=theme.FONT_SMALL,
                          text_color=theme.TEXT_MUTED)
    status.pack(side="left")

    pin_button = ctk.CTkButton(
        header, text="Pinned", width=64, height=30, font=theme.FONT_SMALL,
        fg_color=theme.SUBTLE_BUTTON, hover_color=theme.SUBTLE_BUTTON_HOVER,
        text_color=theme.BUDDY_TEXT, corner_radius=15, command=on_pin_toggle,
    )
    pin_button.pack(side="right", padx=(0, 16))

    folder_button = ctk.CTkButton(
        header, text="Folder", width=64, height=30, font=theme.FONT_SMALL,
        fg_color=theme.SUBTLE_BUTTON, hover_color=theme.SUBTLE_BUTTON_HOVER,
        text_color=theme.BUDDY_TEXT, corner_radius=15,
        command=lambda: os.startfile(DOCS_DIR),
    )
    folder_button.pack(side="right", padx=(0, 8))

    return {"dot": dot, "status": status, "pin_button": pin_button}


def build_input_bar(window):
    bar = ctk.CTkFrame(window, fg_color=theme.WINDOW_BG, corner_radius=0)
    bar.pack(fill="x", side="bottom", padx=14, pady=(6, 14))

    entry = ctk.CTkEntry(
        bar, placeholder_text="Ask something about your PDFs...",
        height=44, corner_radius=22, border_width=0, font=theme.FONT_BODY,
        fg_color=theme.INPUT_BG, text_color=theme.BUDDY_TEXT,
        placeholder_text_color=theme.TEXT_MUTED,
    )
    entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    send_button = ctk.CTkButton(
        bar, text="Send", width=70, height=44, corner_radius=22,
        font=(theme.FONT_FAMILY, 13, "bold"),
        fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
    )
    send_button.pack(side="left")
    return entry, send_button


def set_status(header, text, color):
    header["status"].configure(text=text)
    header["dot"].configure(text_color=color)


def start_widget():
    DOCS_DIR.mkdir(exist_ok=True)
    ctk.set_appearance_mode("dark")

    window = ctk.CTk(fg_color=theme.WINDOW_BG)
    window.title("QueryBuddy")
    window.geometry("440x660")
    window.minsize(340, 440)
    window.attributes("-topmost", True)

    results = queue.Queue()
    state = {"syncing": False, "snapshot": None, "pinned": True}

    def toggle_pin():
        state["pinned"] = not state["pinned"]
        window.attributes("-topmost", state["pinned"])
        header["pin_button"].configure(text="Pinned" if state["pinned"] else "Pin")

    header = build_header(window, toggle_pin)
    entry, send_button = build_input_bar(window)
    chat = chat_view.create_chat_view(window)
    chat["frame"].pack(fill="both", expand=True, padx=10, pady=(6, 0))

    def start_sync():
        if state["syncing"]:
            return
        state["syncing"] = True
        set_status(header, "Reading PDFs...", theme.STATUS_BUSY)
        # remember what the folder looked like when this sync started
        state["snapshot"] = folder_snapshot()
        run_in_background(sync_documents, results, "sync")

    def handle_sync_done(summary, error):
        state["syncing"] = False
        if error:
            set_status(header, "Could not read documents", theme.STATUS_ERROR)
            chat_view.add_system_message(chat, f"Indexing failed: {error}")
            return
        for name in summary["added"]:
            chat_view.add_system_message(chat, f"Learned {name}")
        for name in summary["removed"]:
            chat_view.add_system_message(chat, f"Forgot {name}")
        count = len(state["snapshot"] or {})
        set_status(header, f"Ready · {count} PDF(s)", theme.STATUS_READY)

    def handle_answer_done(result, error):
        chat_view.hide_typing(chat)
        send_button.configure(state="normal")
        if error:
            chat_view.add_system_message(chat, f"Something went wrong: {error}")
            return
        answer, sources = result
        chat_view.add_buddy_message(chat, answer, sources)

    def send_question(event=None):
        question = entry.get().strip()
        if not question or send_button.cget("state") == "disabled":
            return
        entry.delete(0, "end")
        chat_view.add_user_message(chat, question)
        chat_view.show_typing(chat)
        send_button.configure(state="disabled")
        run_in_background(lambda: answer_question(question), results, "answer")

    def check_results():
        while not results.empty():
            tag, result, error = results.get()
            if tag == "sync":
                handle_sync_done(result, error)
            else:
                handle_answer_done(result, error)
        window.after(200, check_results)

    def watch_folder():
        if not state["syncing"] and folder_snapshot() != state["snapshot"]:
            start_sync()
        window.after(WATCH_INTERVAL_MS, watch_folder)

    send_button.configure(command=send_question)
    entry.bind("<Return>", send_question)

    chat_view.add_system_message(chat, "Drop PDFs into the documents folder and ask me anything.")
    start_sync()
    check_results()
    window.after(WATCH_INTERVAL_MS, watch_folder)
    entry.focus()
    window.mainloop()
