import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import tempfile
import shutil

# For clipboard functionality
import pyperclip

# For LangChain and RAG components
try:
    import chromadb
    from langchain_community.document_loaders import (
        PyPDFLoader,
        UnstructuredWordDocumentLoader,
        UnstructuredExcelLoader,
        UnstructuredMarkdownLoader
    )
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.vectorstores import Chroma

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain components not available. RAG functionality will be limited.")

# ============================================================
# Light green color for LLM responses
# ============================================================
LLM_RESPONSE_BG_COLOR = "#e8f5e9"  # Light green color

# ============================================================
# RAG Configuration
# ============================================================
CHROMA_PERSIST_DIR = "./orinda_chroma_db"
COLLECTION_NAME = "orinda_rag_collection"
EMBEDDING_MODEL = "nomic-embed-text"  # Default embedding model in Ollama
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


# ============================================================
# Document Loading Functions
# ============================================================
def load_document(filepath):
    """Load a single document with the appropriate loader"""
    if not LANGCHAIN_AVAILABLE:
        return "LangChain not available. Cannot load document."

    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            loader = PyPDFLoader(filepath)
        elif ext == '.docx':
            loader = UnstructuredWordDocumentLoader(filepath)
        elif ext == '.xlsx':
            loader = UnstructuredExcelLoader(filepath)
        elif ext == '.md' or ext == '.mdx':
            loader = UnstructuredMarkdownLoader(filepath)
        else:
            return f"Unsupported file type: {ext}"

        documents = loader.load()
        return documents
    except Exception as e:
        return f"Error loading document: {e}"


# ============================================================
# Response Frame with Copy Button
# ============================================================
class ResponseFrame(ttk.Frame):
    def __init__(self, parent, response_text, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.columnconfigure(0, weight=1)

        # Calculate appropriate height based on text content
        line_count = response_text.count('\n') + 1
        char_count = len(response_text)
        estimated_wraps = char_count // 80

        # Combine actual lines and estimated wraps, with min and max constraints
        total_lines = min(30, max(5, line_count + estimated_wraps))

        # Response content with light green background and dynamic height
        self.response_text = tk.Text(self, wrap=tk.WORD, height=total_lines,
                                     font=("Source Sans Pro", 14), bg=LLM_RESPONSE_BG_COLOR)
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
# RAG Tab Class
# ============================================================
class VectorsLLMFrame(ttk.Frame):
    def __init__(self, container, llm_chat_func, get_current_model_func, available_models, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        # Store reference to the LLM chat function and model functions
        self.llm_chat_func = llm_chat_func
        self.get_current_model = get_current_model_func
        self.available_models = available_models

        # Create a temp directory for document processing
        self.temp_dir = tempfile.mkdtemp(prefix="orinda_rag_")

        # Initialize ChromaDB
        self.initialize_chroma_db()

        # Track loaded documents
        self.loaded_documents = {}  # filename -> document object

        # Create UI
        self.create_ui()

    def __del__(self):
        """Clean up temp directory when object is destroyed"""
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def initialize_chroma_db(self):
        """Initialize ChromaDB with LangChain"""
        self.vectorstore = None
        self.collection = None

        if not LANGCHAIN_AVAILABLE:
            return

        try:
            # Create the persist directory if it doesn't exist
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

            # Initialize embeddings
            self.embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

            # Initialize or load the existing vector store
            self.vectorstore = Chroma(
                persist_directory=CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings,
                collection_name=COLLECTION_NAME
            )

            # Get document count
            self.document_count = len(self.vectorstore.get()["ids"]) if hasattr(self.vectorstore, "get") else 0

            print(f"ChromaDB initialized with {self.document_count} documents")

        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self.vectorstore = None

    def create_ui(self):
        """Create the user interface for the RAG tab"""
        # Title
        title_label = ttk.Label(self, text="RAG", font=("Source Sans Pro", 18, "bold"))
        title_label.pack(padx=10, pady=5, anchor="w")

        # Model selector frame
        model_frame = ttk.Frame(self)
        model_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(model_frame, text="Select Model:", font=("Source Sans Pro", 14)).pack(side="left")

        # Model dropdown
        self.model_var = tk.StringVar(value=self.get_current_model())
        self.model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=self.available_models,
            state="readonly",
            width=15,
            font=("Source Sans Pro", 14)
        )
        self.model_dropdown.pack(side="left", padx=5)

        # File upload frame
        upload_frame = ttk.Frame(self)
        upload_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(upload_frame, text="Upload Files", command=self.upload_files).pack(side="left")

        # Add file format note
        format_note = ttk.Label(upload_frame, text="Supported Formats: PDF, DOCX, XLSX, and MDX",
                                font=("Source Sans Pro", 12), foreground="#555555")
        format_note.pack(side="left", padx=10)

        self.upload_status = ttk.Label(upload_frame, text="", font=("Source Sans Pro", 14))
        self.upload_status.pack(side="left", padx=10)

        # Progress frame
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill="x", padx=10, pady=5)
        self.progress_label = ttk.Label(self.progress_frame, text="Processing:", font=("Source Sans Pro", 14))
        self.progress_label.pack(side="left")
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate", length=400)
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)
        self.progress_status = ttk.Label(self.progress_frame, text="0%", font=("Source Sans Pro", 14))
        self.progress_status.pack(side="left", padx=5)

        # Hide progress bar initially
        self.progress_frame.pack_forget()

        # File list frame
        listbox_frame = ttk.Frame(self)
        listbox_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10), ipady=10)

        file_header_frame = ttk.Frame(listbox_frame)
        file_header_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(file_header_frame, text="Uploaded Files:", font=("Source Sans Pro", 14, "bold")).pack(side="left")

        self.remove_file_button = ttk.Button(file_header_frame, text="Remove Selected",
                                             command=self.remove_selected_file)
        self.remove_file_button.pack(side="right")

        self.uploaded_files_list = tk.Listbox(listbox_frame, font=("Source Sans Pro", 14), height=5)
        self.uploaded_files_list.pack(fill="both", expand=True)

        # Query frame
        query_frame = ttk.Frame(self)
        query_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(query_frame, text="Enter Query:", font=("Source Sans Pro", 14)).pack(side="left")

        # Switch from Entry to Text for multiline query input
        self.query_text = tk.Text(query_frame, height=3, font=("Source Sans Pro", 14), wrap=tk.WORD)
        self.query_text.pack(side="left", fill="x", expand=True, padx=5)

        buttons_frame = ttk.Frame(query_frame)
        buttons_frame.pack(side="right", padx=5)

        self.rag_button = ttk.Button(buttons_frame, text="Search & Generate",
                                     command=self.perform_rag)
        self.rag_button.pack(side="top", pady=2)

        self.clear_button = ttk.Button(buttons_frame, text="Clear Query",
                                       command=self.clear_query)
        self.clear_button.pack(side="top", pady=2)

        # Results display with adjustable size
        self.results_frame = ttk.Frame(self)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        results_header_frame = ttk.Frame(self.results_frame)
        results_header_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(results_header_frame, text="Results:", font=("Source Sans Pro", 14, "bold")).pack(side="left")

        # Create a scrollable frame for results
        self.results_canvas = tk.Canvas(self.results_frame)
        results_scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_canvas.yview)

        # Configure the canvas
        self.results_canvas.configure(yscrollcommand=results_scrollbar.set)
        results_scrollbar.pack(side="right", fill="y")
        self.results_canvas.pack(side="left", fill="both", expand=True)

        # Container inside canvas for results
        self.results_container = ttk.Frame(self.results_canvas)
        self.results_window = self.results_canvas.create_window((0, 0), window=self.results_container, anchor="nw")

        # Update canvas scroll region when container size changes
        self.results_container.bind("<Configure>", self.on_frame_configure)
        self.results_canvas.bind("<Configure>", self.on_canvas_configure)

        # Initial empty state for results
        self.results_response_frame = None

        # Check LangChain availability
        if not LANGCHAIN_AVAILABLE:
            self.show_error("LangChain components not available. Please install required packages.")

    def on_frame_configure(self, event):
        """Update the scrollregion of the canvas when the inner frame changes size"""
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """When canvas is resized, also resize the inner frame to match"""
        self.results_canvas.itemconfig(self.results_window, width=event.width)

    def clear_query(self):
        """Clear the query text field"""
        self.query_text.delete(1.0, tk.END)

    def update_progress(self, step, total, message="Processing"):
        """Update the progress bar"""
        self.progress_frame.pack(fill="x", padx=10, pady=5, after=self.upload_status.winfo_parent())
        percentage = int((step / total) * 100)
        self.progress_bar["value"] = percentage
        self.progress_status.config(text=f"{percentage}%")
        self.progress_label.config(text=f"{message}:")
        self.update_idletasks()

    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_frame.pack_forget()
        self.update_idletasks()

    def upload_files(self):
        """Upload and process files using LangChain and ChromaDB"""
        if not LANGCHAIN_AVAILABLE:
            messagebox.showerror("Missing Dependencies",
                                 "LangChain components not available. Please install required packages.")
            return

        filetypes = [
            ("Document Files", "*.pdf;*.docx;*.xlsx;*.md;*.mdx"),
            ("PDF Files", "*.pdf"),
            ("Word Documents", "*.docx"),
            ("Excel Files", "*.xlsx"),
            ("Markdown Files", "*.md;*.mdx")
        ]

        files = filedialog.askopenfilenames(title="Select Files for RAG", filetypes=filetypes)
        if not files:
            return

        # Show progress bar
        self.update_progress(0, 1, "Initializing")

        # Process files in a background thread
        def process_files_thread():
            total_docs = 0
            processed_docs = 0

            # First load all documents to get the total count
            all_documents = []
            for filepath in files:
                filename = os.path.basename(filepath)
                self.after(0, lambda file=filename: self.update_progress(0, 1, f"Loading {file}"))

                try:
                    docs = load_document(filepath)
                    if isinstance(docs, str):  # Error message
                        self.after(0, lambda msg=docs: self.upload_status.config(text=msg))
                        continue

                    # Add to our document list
                    all_documents.append((filename, docs))
                    total_docs += len(docs)
                except Exception as e:
                    self.after(0, lambda err=str(e): self.upload_status.config(text=f"Error: {err}"))

            if not all_documents:
                self.after(0, lambda: self.hide_progress())
                self.after(0, lambda: self.upload_status.config(text="No documents were successfully loaded."))
                return

            # Now process and add to vector store
            try:
                # Initialize text splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP
                )

                # Process each document
                for filename, docs in all_documents:
                    self.after(0, lambda file=filename: self.update_progress(
                        processed_docs, total_docs, f"Processing {file}"))

                    # Split the documents
                    splits = text_splitter.split_documents(docs)

                    # Add file identifier to metadata
                    for split in splits:
                        if not split.metadata:
                            split.metadata = {}
                        split.metadata["source"] = filename

                    # Add to vector store
                    if not self.vectorstore:
                        # Initialize a new vector store if none exists
                        self.vectorstore = Chroma.from_documents(
                            documents=splits,
                            embedding=self.embeddings,
                            persist_directory=CHROMA_PERSIST_DIR,
                            collection_name=COLLECTION_NAME
                        )
                    else:
                        # Add to existing vector store
                        self.vectorstore.add_documents(splits)

                    # Add to UI list
                    self.after(0, lambda file=filename: self.uploaded_files_list.insert(tk.END, file))

                    # Update progress
                    processed_docs += len(docs)
                    self.after(0, lambda current=processed_docs, total=total_docs:
                    self.update_progress(current, total, "Embedding"))

                # Persist the changes
                if hasattr(self.vectorstore, "persist"):
                    self.vectorstore.persist()

                # Update status
                self.after(0, lambda: self.upload_status.config(
                    text=f"Successfully processed {processed_docs} documents from {len(all_documents)} files."))

            except Exception as e:
                self.after(0, lambda err=str(e): self.upload_status.config(text=f"Error during processing: {err}"))

            finally:
                # Hide progress bar
                self.after(0, lambda: self.hide_progress())

        # Start the processing thread
        thread = threading.Thread(target=process_files_thread)
        thread.daemon = True
        thread.start()

    def remove_selected_file(self):
        """Remove the selected file from the UI list"""
        selection = self.uploaded_files_list.curselection()
        if not selection:
            messagebox.showinfo("Remove File", "Please select a file to remove.")
            return

        # Get selected filename
        filename = self.uploaded_files_list.get(selection[0])

        # Confirm deletion
        confirm = messagebox.askyesno("Remove File",
                                      f"Are you sure you want to remove '{filename}'?\n\n"
                                      f"Note: This will only remove it from the list. To completely remove "
                                      f"the document from the vector database, you need to restart the application.")
        if not confirm:
            return

        # Remove from listbox
        self.uploaded_files_list.delete(selection[0])
        self.upload_status.config(text=f"Removed '{filename}' from list.")

        # Note: Actually removing from ChromaDB would require rebuilding the collection
        # which is complex. We'll just remove from the UI for now.

    def perform_rag(self):
        """Perform RAG query with the selected model"""
        if not LANGCHAIN_AVAILABLE or not self.vectorstore:
            messagebox.showerror("RAG Error", "Vector database not initialized. Please upload documents first.")
            return

        # Get query text
        query = self.query_text.get("1.0", tk.END).strip()
        if not query:
            messagebox.showerror("Input Error", "Please enter a query.")
            return

        # Get current model
        current_model = self.model_var.get()

        # Show progress
        self.update_progress(0, 1, "Searching")

        # Disable button during processing
        self.rag_button.config(state="disabled")

        # Process in background thread
        def rag_thread():
            try:
                # Step 1: Update progress
                self.after(0, lambda: self.update_progress(1, 3, "Finding similar documents"))

                # Step 2: Search for similar documents
                results = self.vectorstore.similarity_search_with_relevance_scores(query, k=3)

                # Filter results with a score below threshold (0.7)
                relevant_results = [(doc, score) for doc, score in results if score > 0.7]

                # If no relevant results, widen the threshold
                if not relevant_results and results:
                    relevant_results = results[:2]  # Just take top 2

                # Update progress
                self.after(0, lambda: self.update_progress(2, 3, "Generating response"))

                # Format context from results
                if relevant_results:
                    context_parts = []
                    for doc, score in relevant_results:
                        source = doc.metadata.get("source", "unknown")
                        relevance = int(score * 100)
                        context_parts.append(f"[Source: {source}, Relevance: {relevance}%]\n{doc.page_content}")

                    context = "\n\n".join(context_parts)
                else:
                    context = "No relevant information found in the knowledge base."

                # Create prompt with the context
                prompt = (
                    f"### Context from Knowledge Base:\n\n{context}\n\n"
                    f"### User Query:\n{query}\n\n"
                    f"### Instructions:\n"
                    f"Based ONLY on the information provided in the context above, "
                    f"please answer the user's query. If the context doesn't contain "
                    f"relevant information to answer the query, state that clearly. "
                    f"Include references to the source documents where appropriate."
                )

                # Get LLM response using the provided chat function
                response = self.llm_chat_func(prompt, current_model)

                # Update progress
                self.after(0, lambda: self.update_progress(3, 3, "Completed"))

                # Update results in main thread
                self.after(0, lambda resp=response: self.update_results(resp))

            except Exception as e:
                # Handle errors
                error_msg = f"Error during RAG process: {str(e)}"
                self.after(0, lambda err=error_msg: self.show_error(err))

            finally:
                # Re-enable button and hide progress in main thread
                self.after(0, lambda: self.rag_button.config(state="normal"))
                self.after(0, lambda: self.hide_progress())

        # Start the thread
        thread = threading.Thread(target=rag_thread)
        thread.daemon = True
        thread.start()

    def update_results(self, response):
        """Update the results display with the RAG response"""
        # Clear previous results if any
        if self.results_response_frame:
            self.results_response_frame.destroy()

        # Create new response frame with copy button
        self.results_response_frame = ResponseFrame(self.results_container, response)
        self.results_response_frame.pack(fill="both", expand=True)

        # Update canvas scroll region
        self.results_canvas.update_idletasks()
        self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

        # Scroll to top of results
        self.results_canvas.yview_moveto(0.0)

    def show_error(self, error_message):
        """Show an error when RAG processing fails"""
        messagebox.showerror("RAG Error", error_message)
