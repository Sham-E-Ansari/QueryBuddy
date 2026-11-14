import customtkinter as ctk

from gui import theme

BUBBLE_WIDTH_RATIO = 0.78  # how much of the window a bubble may fill


def create_chat_view(parent):
    """Scrollable message area. Returns a dict we pass to the add_* functions."""
    frame = ctk.CTkScrollableFrame(
        parent, fg_color=theme.CHAT_BG, corner_radius=0,
        scrollbar_button_color=theme.SUBTLE_BUTTON,
        scrollbar_button_hover_color=theme.SUBTLE_BUTTON_HOVER,
    )
    view = {"frame": frame, "labels": [], "typing_row": None, "typing_label": None, "typing_job": None}
    frame.bind("<Configure>", lambda event: resize_bubbles(view, event.width))
    return view


def resize_bubbles(view, frame_width):
    wrap = max(int(frame_width * BUBBLE_WIDTH_RATIO) - 32, 120)
    for label in view["labels"]:
        label.configure(wraplength=wrap)


def scroll_to_bottom(view):
    frame = view["frame"]
    frame.update_idletasks()
    frame._parent_canvas.yview_moveto(1.0)


def copy_to_clipboard(widget, text, button):
    widget.clipboard_clear()
    widget.clipboard_append(text)
    button.configure(text="Copied")
    button.after(1200, lambda: button.configure(text="Copy"))


def make_row(view):
    row = ctk.CTkFrame(view["frame"], fg_color="transparent")
    row.pack(fill="x", pady=(0, 10), padx=4)
    return row


def make_bubble(view, row, text, side, bg, fg):
    bubble = ctk.CTkFrame(row, fg_color=bg, corner_radius=theme.BUBBLE_RADIUS)
    bubble.pack(anchor="e" if side == "right" else "w")
    label = ctk.CTkLabel(
        bubble, text=text, text_color=fg, font=theme.FONT_BODY,
        justify="left", anchor="w", wraplength=300,
    )
    label.pack(padx=14, pady=10)
    view["labels"].append(label)
    return bubble


def add_user_message(view, text):
    row = make_row(view)
    make_bubble(view, row, text, "right", theme.USER_BUBBLE, theme.USER_TEXT)
    scroll_to_bottom(view)


def add_buddy_message(view, text, sources=None):
    row = make_row(view)
    make_bubble(view, row, text, "left", theme.BUDDY_BUBBLE, theme.BUDDY_TEXT)

    footer = ctk.CTkFrame(row, fg_color="transparent")
    footer.pack(anchor="w", pady=(4, 0), padx=4)

    copy_button = ctk.CTkButton(
        footer, text="Copy", width=48, height=22, font=theme.FONT_SMALL,
        fg_color="transparent", hover_color=theme.SUBTLE_BUTTON,
        text_color=theme.TEXT_MUTED, corner_radius=8,
    )
    copy_button.configure(
        command=lambda: copy_to_clipboard(view["frame"], text, copy_button)
    )
    copy_button.pack(side="left")

    if sources:
        source_label = ctk.CTkLabel(
            footer, text="  |  " + "  ·  ".join(sources),
            font=theme.FONT_SMALL, text_color=theme.TEXT_MUTED,
            justify="left", wraplength=280,
        )
        source_label.pack(side="left")
        view["labels"].append(source_label)

    scroll_to_bottom(view)


def add_system_message(view, text):
    label = ctk.CTkLabel(
        view["frame"], text=text, font=theme.FONT_SMALL,
        text_color=theme.TEXT_MUTED, wraplength=300, justify="center",
    )
    label.pack(pady=(0, 10))
    view["labels"].append(label)
    scroll_to_bottom(view)


def animate_typing(view, label, step):
    label.configure(text="Thinking" + "." * (step % 4))
    view["typing_job"] = label.after(400, lambda: animate_typing(view, label, step + 1))


def show_typing(view):
    if view["typing_row"] is not None:
        return
    row = make_row(view)
    make_bubble(view, row, "Thinking", "left", theme.BUDDY_BUBBLE, theme.TEXT_MUTED)
    label = view["labels"][-1]
    view["typing_row"] = row
    view["typing_label"] = label
    animate_typing(view, label, 1)
    scroll_to_bottom(view)


def hide_typing(view):
    row = view["typing_row"]
    if row is None:
        return
    view["typing_label"].after_cancel(view["typing_job"])
    view["labels"].remove(view["typing_label"])
    row.destroy()
    view["typing_row"] = None
    view["typing_label"] = None
