import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from ollama import chat, ChatResponse, list as list_models
import threading
import sqlite3
import datetime

# For clipboard functionality
import pyperclip

# Import the RAG tab module
from rag_tab import VectorsLLMFrame

# ============================================================
# Global Settings
# ============================================================
DATABASE_FILE = "orinda_chats.db"

# Light green color for LLM responses
LLM_RESPONSE_BG_COLOR = "#e8f5e9"  # Light green color

# Available models
AVAILABLE_MODELS = [
    "llama3:70b",
    "llama3:latest",
    "llama3.2:latest"
]

# Default model
DEFAULT_MODEL = "llama3.2:latest"

# Font settings
FONT_FAMILY = "Source Sans Pro"
FONT_SIZE = 14
BASE_FONT = (FONT_FAMILY, FONT_SIZE)
HEADING_FONT = (FONT_FAMILY, FONT_SIZE + 4, "bold")
SMALL_FONT = (FONT_FAMILY, FONT_SIZE - 2)


# ============================================================
# Database Setup
# ============================================================
def setup_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()


def save_chat_to_db(title, content):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO saved_chats (title, content, timestamp) VALUES (?, ?, ?)",
                   (title, content, timestamp))
    conn.commit()
    conn.close()


def get_saved_chats():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, timestamp FROM saved_chats ORDER BY timestamp DESC")
    chats = cursor.fetchall()
    conn.close()
    return chats


def get_chat_by_id(chat_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM saved_chats WHERE id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def delete_chat_by_id(chat_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


# ============================================================
# LLM Chat Function using Ollama
# ============================================================
def get_model_info(model_name):
    """Get information about the specified model"""
    try:
        # Try to get detailed model information from Ollama
        models = list_models()
        for model in models.get('models', []):
            if model.get('name') == model_name:
                return {
                    "name": model.get('name'),
                    "version": model.get('digest', '').split(':')[-1][:7],
                    "size": f"{model.get('size') / (1024 * 1024 * 1024):.1f}GB" if model.get('size') else "Unknown",
                    "modified": model.get('modified_at', 'Unknown')
                }
        # If detailed info not found, return basic info
        return {
            "name": model_name,
            "version": "Unknown"
        }
    except Exception as e:
        print(f"Error getting model info: {e}")
        return {
            "name": model_name,
            "version": "Unknown"
        }


def llm_chat(query, model_name):
    try:
        response: ChatResponse = chat(
            model=model_name,
            messages=[{"role": "user", "content": query}]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error calling Ollama: {e}"


# ============================================================
# Response Frame with Copy Button
# ============================================================
class ResponseFrame(ttk.Frame):
    def __init__(self, parent, response_text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.columnconfigure(0, weight=1)

        # Response content with light green background
        self.response_text = tk.Text(self, wrap=tk.WORD, height=min(8, response_text.count('\n') + 2),
                                     font=BASE_FONT, bg=LLM_RESPONSE_BG_COLOR)  # Set light green background
        self.response_text.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.response_text.insert(tk.END, response_text)
        self.response_text.config(state=tk.DISABLED)

        # Copy button
        self.copy_button = ttk.Button(self, text="📋 Copy", command=self.copy_to_clipboard)
        self.copy_button.grid(row=0, column=1, sticky="ne")

    def copy_to_clipboard(self):
        text = self.response_text.get(1.0, tk.END).strip()
        pyperclip.copy(text)

        # Visual feedback for copy action
        original_text = self.copy_button["text"]
        self.copy_button["text"] = "✓ Copied!"

        # Reset button text after 1.5 seconds
        self.after(1500, lambda: self.copy_button.configure(text=original_text))


# ============================================================
# LLM Chat Tab
# ============================================================
class ChatFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        # Get reference to parent app for model access
        self.parent_app = self.winfo_toplevel()

        # Get initial model information
        self.current_model = DEFAULT_MODEL
        self.model_info = get_model_info(self.current_model)

        # Create paned window to split the tab into chat and history areas
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Left panel - Chat area
        self.chat_panel = ttk.Frame(self.paned)
        self.paned.add(self.chat_panel, weight=3)

        # Title and model selection area
        header_frame = ttk.Frame(self.chat_panel)
        header_frame.pack(fill="x", anchor="w", pady=(0, 10))

        # Title for chat section
        ttk.Label(header_frame, text="Chat Session", font=HEADING_FONT).pack(side="left", anchor="w")

        # Add model switcher dropdown
        model_frame = ttk.Frame(self.chat_panel)
        model_frame.pack(fill="x", pady=(0, 10))

        # Model info display
        self.model_info_var = tk.StringVar(value=f"Using: {self.current_model} (Version: {self.model_info['version']})")
        self.model_info_label = ttk.Label(
            model_frame,
            textvariable=self.model_info_var,
            font=BASE_FONT,
            foreground="#555555"  # Subtle gray color
        )
        self.model_info_label.pack(side="left", anchor="w")

        # Add model selector
        ttk.Label(model_frame, text="   Switch Model:", font=BASE_FONT).pack(side="left", padx=(20, 5))

        self.model_var = tk.StringVar(value=self.current_model)
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=AVAILABLE_MODELS,
            state="readonly",
            width=15,
            font=BASE_FONT
        )
        self.model_dropdown.pack(side="left", padx=5)
        self.model_dropdown.bind("<<ComboboxSelected>>", self.on_model_change)

        # Chat display
        self.chat_container = ttk.Frame(self.chat_panel)
        self.chat_container.pack(fill="both", expand=True, pady=(0, 10))

        # Scrollable canvas for messages
        self.canvas = tk.Canvas(self.chat_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.chat_container, orient="vertical", command=self.canvas.yview)
        self.chat_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Create a window inside the canvas to hold all messages
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")

        # Update canvas scroll region when frame size changes
        self.chat_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Processing indicator
        self.processing_frame = ttk.Frame(self.chat_panel)
        self.processing_frame.pack(fill="x", pady=(0, 10))
        self.processing_indicator = ttk.Progressbar(self.processing_frame, mode="indeterminate")
        self.processing_label = ttk.Label(self.processing_frame, text="Processing...", font=BASE_FONT)

        # Input area
        input_frame = ttk.Frame(self.chat_panel)
        input_frame.pack(fill="x")
        self.entry = ttk.Entry(input_frame, font=BASE_FONT)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", lambda event: self.send_message())
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side="left")

        # Button Frame
        button_frame = ttk.Frame(self.chat_panel)
        button_frame.pack(fill="x", pady=(10, 0))

        # Save Chat button
        self.save_button = ttk.Button(button_frame, text="Save Chat", command=self.save_chat_dialog)
        self.save_button.pack(side="left", padx=(0, 5))

        # New Chat button
        self.new_chat_button = ttk.Button(button_frame, text="Start New Chat", command=self.start_new_chat)
        self.new_chat_button.pack(side="left", padx=(0, 5))

        # Right panel - History area
        self.history_panel = ttk.Frame(self.paned)
        self.paned.add(self.history_panel, weight=1)

        ttk.Label(self.history_panel, text="Saved Chats", font=HEADING_FONT).pack(anchor="w", pady=(0, 5))

        # History listbox
        self.history_listbox = tk.Listbox(self.history_panel, font=BASE_FONT)
        self.history_listbox.pack(fill="both", expand=True, pady=(0, 5))
        self.history_listbox.bind("<<ListboxSelect>>", self.load_selected_chat)

        # History management buttons
        history_button_frame = ttk.Frame(self.history_panel)
        history_button_frame.pack(fill="x")

        # Delete selected chat button
        self.delete_button = ttk.Button(history_button_frame, text="Delete Chat", command=self.delete_selected_chat)
        self.delete_button.pack(side="left", padx=(0, 5))

        # Store chat IDs separately
        self.chat_ids = []
        self.response_frames = []

        # Refresh history list
        self.refresh_chat_history()

    def on_model_change(self, event):
        """Handle model selection change"""
        # Get the selected model
        new_model = self.model_var.get()

        # Update current model
        self.current_model = new_model

        # Update parent app's model
        self.parent_app.current_model = new_model

        # Get updated model info
        self.model_info = get_model_info(new_model)

        # Update the model info display
        self.model_info_var.set(f"Using: {new_model} (Version: {self.model_info['version']})")

        # Provide feedback
        messagebox.showinfo("Model Changed", f"Switched to model: {new_model}")

        # Start a new chat with the new model
        self.start_new_chat()

    def on_frame_configure(self, event):
        """Update the scrollregion of the canvas when the inner frame changes size"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """When canvas is resized, also resize the inner frame to match"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def show_processing(self):
        self.processing_label.pack(side="left")
        self.processing_indicator.pack(side="left", fill="x", expand=True, padx=5)
        self.processing_indicator.start(10)

    def hide_processing(self):
        self.processing_indicator.stop()
        self.processing_indicator.pack_forget()
        self.processing_label.pack_forget()

    def send_message(self):
        query = self.entry.get().strip()
        if not query:
            messagebox.showerror("Input Error", "Please enter a message before sending.")
            return

        # Display user message
        user_label = ttk.Label(self.chat_frame, text=f"You:", font=HEADING_FONT)
        user_label.pack(anchor="w", padx=5, pady=(10, 0))

        user_message = ttk.Label(self.chat_frame, text=query, wraplength=400, font=BASE_FONT)
        user_message.pack(anchor="w", padx=20, pady=(0, 10))

        self.entry.delete(0, tk.END)

        # Show processing indicator
        self.show_processing()
        self.update_idletasks()  # Force UI update

        # Scroll to bottom
        self.canvas.yview_moveto(1.0)

        # Process in background thread
        def process_message():
            response = llm_chat(query, self.current_model)

            # Update UI in main thread
            self.after(0, lambda: self.show_response(response))

        thread = threading.Thread(target=process_message)
        thread.daemon = True
        thread.start()

    def show_response(self, response):
        # Hide processing indicator
        self.hide_processing()

        # Show response
        llm_label = ttk.Label(self.chat_frame, text="LLM:", font=HEADING_FONT)
        llm_label.pack(anchor="w", padx=5, pady=(10, 0))

        # Create response frame with copy button
        response_frame = ResponseFrame(self.chat_frame, response)
        response_frame.pack(anchor="w", fill="x", padx=20, pady=(0, 10))

        # Keep track of response frames
        self.response_frames.append(response_frame)

        # Scroll to bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def save_chat_dialog(self):
        # Extract all text content from the chat
        chat_text = ""
        for widget in self.chat_frame.winfo_children():
            if isinstance(widget, ttk.Label):
                chat_text += widget.cget("text") + "\n"
            elif isinstance(widget, ResponseFrame):
                chat_text += widget.response_text.get(1.0, tk.END) + "\n"

        chat_text = chat_text.strip()
        if not chat_text:
            messagebox.showinfo("Save Chat", "No chat history to save.")
            return

        # Add the model info to the chat text
        model_info = f"[Model: {self.current_model}]\n\n"
        chat_text = model_info + chat_text

        title = simpledialog.askstring("Save Chat", "Enter a title for this chat:")
        if title:
            save_chat_to_db(title, chat_text)
            messagebox.showinfo("Save Chat", "Chat saved successfully.")
            self.refresh_chat_history()

    def start_new_chat(self):
        # Clear all widgets from chat frame
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

        # Reset response frames list
        self.response_frames = []

        # Add a welcome message with model info
        welcome_label = ttk.Label(self.chat_frame, text="LLM:", font=HEADING_FONT)
        welcome_label.pack(anchor="w", padx=5, pady=(10, 0))

        welcome_text = f"Welcome to a new chat session with {self.current_model}! How can I help you today?"
        welcome_frame = ResponseFrame(self.chat_frame, welcome_text)
        welcome_frame.pack(anchor="w", fill="x", padx=20, pady=(0, 10))

        self.response_frames.append(welcome_frame)

        # Update canvas
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(0.0)

    def refresh_chat_history(self):
        self.history_listbox.delete(0, tk.END)
        self.chat_ids = []  # Clear the existing IDs

        for chat_id, title, timestamp in get_saved_chats():
            display_text = f"{title} ({timestamp})"
            self.history_listbox.insert(tk.END, display_text)
            self.chat_ids.append(chat_id)  # Store ID in parallel list

    def load_selected_chat(self, event):
        selection = self.history_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if 0 <= index < len(self.chat_ids):
            chat_id = self.chat_ids[index]
            content = get_chat_by_id(chat_id)

            if content:
                # Clear current chat
                for widget in self.chat_frame.winfo_children():
                    widget.destroy()

                # Display chat content
                lines = content.strip().split('\n')
                i = 0

                # Check if there's model info at the beginning
                if i < len(lines) and lines[i].startswith('[Model:'):
                    model_line = lines[i]

                    # Extract model name and display it, but don't change current model
                    try:
                        model_name = model_line.split('[Model:')[1].split(']')[0].strip()
                        model_info_label = ttk.Label(
                            self.chat_frame,
                            text=f"This chat used model: {model_name}",
                            font=SMALL_FONT,
                            foreground="#555555"
                        )
                        model_info_label.pack(anchor="w", padx=5, pady=(5, 10))
                    except:
                        pass  # If there's an error parsing, just skip

                    # Skip the model line and the empty line after it
                    i += 2

                # Process the rest of the chat
                while i < len(lines):
                    if lines[i].endswith(':'):  # This is a speaker indicator
                        speaker = lines[i]
                        message_lines = []
                        i += 1

                        # Collect all lines of the message until next speaker
                        while i < len(lines) and not lines[i].endswith(':'):
                            message_lines.append(lines[i])
                            i += 1

                        message = '\n'.join(message_lines)

                        if speaker == "You:":
                            # Display user message
                            user_label = ttk.Label(self.chat_frame, text=speaker, font=HEADING_FONT)
                            user_label.pack(anchor="w", padx=5, pady=(10, 0))

                            user_message = ttk.Label(self.chat_frame, text=message, wraplength=400, font=BASE_FONT)
                            user_message.pack(anchor="w", padx=20, pady=(0, 10))
                        else:
                            # Display LLM message with copy button
                            llm_label = ttk.Label(self.chat_frame, text=speaker, font=HEADING_FONT)
                            llm_label.pack(anchor="w", padx=5, pady=(10, 0))

                            # Create response frame with copy button
                            response_frame = ResponseFrame(self.chat_frame, message)
                            response_frame.pack(anchor="w", fill="x", padx=20, pady=(0, 10))
                            self.response_frames.append(response_frame)
                    else:
                        # Skip any unexpected lines
                        i += 1

                # Scroll to top
                self.canvas.update_idletasks()
                self.canvas.yview_moveto(0.0)

    def delete_selected_chat(self):
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showinfo("Delete Chat", "Please select a chat to delete.")
            return

        index = selection[0]
        if 0 <= index < len(self.chat_ids):
            chat_id = self.chat_ids[index]

            # Confirm deletion
            confirm = messagebox.askyesno("Delete Chat",
                                          "Are you sure you want to delete this chat? This action cannot be undone.")
            if confirm:
                delete_chat_by_id(chat_id)
                messagebox.showinfo("Delete Chat", "Chat deleted successfully.")
                self.refresh_chat_history()


# ============================================================
# Main Application: Orinda
# ============================================================
class OrindaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Orinda")
        self.geometry("1200x800")  # Increased size for better spacing

        # Set current model
        self.current_model = DEFAULT_MODEL

        # Create themes directory if it doesn't exist
        themes_dir = os.path.join(os.path.dirname(__file__), "themes")
        if not os.path.exists(themes_dir):
            os.makedirs(themes_dir)

        # Create light subdirectory for images
        light_dir = os.path.join(themes_dir, "light")
        if not os.path.exists(light_dir):
            os.makedirs(light_dir)

        # Set up app styling
        self.style = ttk.Style(self)

        # Try to use the park theme (keeping existing theme setup)
        tcl_path = os.path.join(themes_dir, "park_light.tcl")
        try:
            # Account for the difference in theme name (park-light in tcl file, park_light in our code)
            self.tk.call("source", tcl_path)
            self.style.theme_use("park-light")
            print("Successfully loaded park-light theme")
        except tk.TclError as e:
            print(f"Could not load theme: {e}")
            # Set up a fallback clean appearance
            self.style.configure("TButton", padding=6, relief="flat")
            self.style.configure("TFrame", background="#ffffff")
            self.style.configure("TLabel", background="#ffffff")
            self.style.configure("TNotebook", background="#ffffff")
            self.style.configure("TNotebook.Tab", padding=[12, 4], background="#f0f0f0")

        # Configure default font
        self.option_add("*Font", BASE_FONT)

        # Override font for specific widgets
        self.style.configure("TLabel", font=BASE_FONT)
        self.style.configure("TButton", font=BASE_FONT)
        self.style.configure("TEntry", font=BASE_FONT)
        self.style.configure("TCombobox", font=BASE_FONT)

        # Modify this section in OrindaApp.__init__ method
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                print("Successfully loaded icon.png")
            except Exception as e:
                print(f"Could not set application icon from icon.png: {e}")
                self.create_default_icon()
        else:
            # Instead of just printing a message, create the default icon without error
            print("Icon file not found, creating default icon")
            self.create_default_icon()

        # Initialize database
        setup_database()

        # App header with logo aligned to left
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=10)

        # Try to load logo and position it on the left
        logo_path = os.path.join(os.path.dirname(__file__), "ORINDA.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img = img.resize((150, 75), Image.Resampling.LANCZOS)  # Slightly smaller for better left alignment
                self.logo_image = ImageTk.PhotoImage(img)
                self.logo_label = ttk.Label(header_frame, image=self.logo_image)
                self.logo_label.pack(side="left", anchor="w")  # Position logo on the left
            except Exception as e:
                print(f"Could not load logo: {e}")
                self.create_text_logo(header_frame)
        else:
            self.create_text_logo(header_frame)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create LLM Chat tab
        self.chat_tab = ChatFrame(self.notebook)
        self.notebook.add(self.chat_tab, text="LLM Chat")

        # Create RAG tab using the imported module
        self.vectors_tab = VectorsLLMFrame(
            self.notebook,
            llm_chat_func=llm_chat,
            get_current_model_func=lambda: self.current_model,
            available_models=AVAILABLE_MODELS
        )
        self.notebook.add(self.vectors_tab, text="RAG")

        # Exit button
        exit_frame = ttk.Frame(self)
        exit_frame.pack(fill="x", padx=10, pady=10)
        exit_button = ttk.Button(exit_frame, text="Exit", command=self.exit_app)
        exit_button.pack(side="right")

    def create_default_icon(self):
        """Create a simple default icon if custom one is not available"""
        try:
            icon = Image.new('RGB', (64, 64), color="#217346")
            photo = ImageTk.PhotoImage(icon)
            self.iconphoto(True, photo)
        except Exception as e:
            print(f"Could not create default icon: {e}")

    def create_text_logo(self, parent_frame):
        """Create a text-based logo as a fallback, aligned to the left"""
        title_label = ttk.Label(parent_frame, text="ORINDA",
                                font=(FONT_FAMILY, 36, "bold"))
        title_label.pack(side="left")

        subtitle_label = ttk.Label(parent_frame, text="LLM Assistant",
                                   font=(FONT_FAMILY, 18))
        subtitle_label.pack(side="left", padx=(10, 0))

    def exit_app(self):
        try:
            # Only attempt to clear the collection if vectorstore exists and has a 'get' method
            if hasattr(self.vectors_tab, 'vectorstore') and self.vectors_tab.vectorstore is not None:
                if hasattr(self.vectors_tab.vectorstore, 'get'):
                    all_docs = self.vectors_tab.vectorstore.get()
                    all_ids = all_docs.get("ids", [])
                    if all_ids:
                        self.vectors_tab.vectorstore.delete(ids=all_ids)
                        print("Chroma collection cleared.")
                else:
                    print("No active collection to clear.")
            else:
                print("No active vectorstore to clear.")
        except Exception as e:
            print(f"Error clearing Chroma collection: {e}")

        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.destroy()


if __name__ == "__main__":
    app = OrindaApp()

    # Start with a new chat session in the LLM Chat tab
    app.chat_tab.start_new_chat()

    app.mainloop()
