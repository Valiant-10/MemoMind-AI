# from google import genai
#from google.auth.environment_vars import PROJECT
from openai import OpenAI
from dotenv import load_dotenv
import customtkinter as ctk
import json
import os
import speech_recognition as sr
import pyttsx3
import queue
import threading
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
from tkinter import filedialog
import shutil
import time
from ddgs import DDGS


# adding we search

# import ollama

# ====================================================
# google CLIENT
# ==================================================== #
load_dotenv()
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

print("Loading Embedding Model")
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)
print("Embedding Model Loaded")

DB_PATH = r"C:\Users\DELL\PycharmProjects\project_llm_python_openrouter\pythonProject\chroma_db"
PDF_FOLDER = r"C:\Users\DELL\PycharmProjects\project_llm_python_openrouter\pythonProject\pdf"
os.makedirs(PDF_FOLDER, exist_ok=True)
chroma_client = chromadb.PersistentClient(
    path=DB_PATH
)
collection = chroma_client.get_or_create_collection(
    name="multi_pdf_collection"
)
memory_collection = chroma_client.get_or_create_collection(
    name="memory_collection"
)
print(f"Documents Indexed: {collection.count()}")

# to check what are the documents actually loaded
sample = collection.peek()
print("\nSample Documents:")
print(sample)
# ====================================================
# MODEL
# ==================================================== #
MODEL_NAME = "llama-3.3-70b-versatile"
BACKUP_MODEL = "llama-3.1-8b-instant"
MAX_TOKENS = 800

CURRENT_PDF = None
all_docs = collection.get()
if all_docs["metadatas"]:
    CURRENT_PDF = all_docs["metadatas"][-1]["source"]



MEMORY_FILE = "memory.json"
CHAT_LOG = "chat_history.txt"

#used for displaying the chat title names in chat history panel
CURRENT_CHAT = None
CHAT_TITLE = None

#creats a chat folder
PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
DB_PATH = os.path.join(
    PROJECT_DIR, "chroma_db"
)
PDF_FOLDER = os.path.join(
    PROJECT_DIR, "pdf"
)

CHATS_FOLDER = os.path.join(
    PROJECT_DIR,
    "chats"
)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(
    CHATS_FOLDER,
    exist_ok=True
)
print(CHATS_FOLDER)
# ====================================================
# TTS QUEUE SYSTEM
stop_speaking = False

# LOAD MEMORY

if os.path.exists(MEMORY_FILE):

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            messages = json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):

        messages = [
            {
                "role": "system",
                "content": "You are MemoMind AI, a friendly AI assistant and Python tutor."
            }
        ]

else:

    messages = [
        {
            "role": "system",
            "content": "You are MemoMind AI, a friendly AI assistant and Python tutor."
        }
    ]
# ====================================================
# GUI SETTINGS
# ==================================================== #

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ====================================================
# MAIN APP
# ==================================================== #

app = ctk.CTk()

app.title("MemoMind AI")

app.geometry("1000x650")


# upload pdf function
def upload_pdf():
    global CURRENT_PDF

    file_path = filedialog.askopenfilename(
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not file_path:
        return

    try:

        file_name = os.path.basename(file_path)
        CURRENT_PDF = file_name
        print("Current PDF:", CURRENT_PDF)

        destination = os.path.join(
            PDF_FOLDER,
            file_name
        )

        shutil.copy(
            file_path,
            destination
        )

        pdf = PdfReader(destination)
        full_text = ""
        all_chunks = []
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            chunk_size = 500
            page_chunks = [
                text[i:i + chunk_size]
                for i in range(0, len(text), chunk_size)
            ]
            for chunk in page_chunks:
                if chunk.strip():
                    all_chunks.append(
                        {
                            "text": chunk.strip(),
                            "page": page_number
                        }
                    )
        start_id = collection.count()

        for i, item in enumerate(all_chunks):
            chunk = item["text"]
            page = item["page"]

            embedding = embedding_model.encode(
                chunk
            ).tolist()

            collection.add(
                ids=[str(start_id + i)],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[
                    {
                        "source": file_name,
                        "page": page
                    }
                ]
            )

        chat_box.insert(
            "end",
            f"\n✅ PDF Uploaded:\n{file_name}\n"
        )

        chat_box.see("end")

        update_doc_count()

    except Exception as e:

        chat_box.insert(
            "end",
            f"\nUpload Error:\n{str(e)}\n"
        )

        chat_box.see("end")


# update_doc_count function
def update_doc_count():
    doc_label.configure(
        text=f"Documents Indexed:\n{collection.count()}"
    )


# ====================================================
# SIDEBAR
# ==================================================== #
#scroll slide bar
sidebar_frame = ctk.CTkScrollableFrame(
    app,
    width=220,
    corner_radius=0
)

sidebar_frame.pack(side="left", fill="y")

# doc_lable function
doc_label = ctk.CTkLabel(
    sidebar_frame,
    text=f"Documents Indexed:\n{collection.count()}",
    font=("Roboto UI", 12)
)

doc_label.pack(
    pady=10
)
# ====================================================
# TITLE
# ==================================================== #

title_label = ctk.CTkLabel(
    sidebar_frame,
    text="MemoMind AI",
    font=("Roboto UI", 22, "bold")
)

title_label.pack(pady=30)
#===================================


#add clear_chat_history function
def clear_chat_history():
    for file in os.listdir(CHATS_FOLDER):
        if file.endswith(".json"):

            os.remove(
                os.path.join(
                    CHATS_FOLDER,file
                )
            )
    refresh_chat_history()
    print("chat history cleared")
    #clear_chat_history = clears only one chat in chat.text not json file
    if CURRENT_CHAT :
        os.remove(
            os.path.join(
                CHATS_FOLDER,
                CURRENT_CHAT
            )
        )
        refresh_chat_history()
#add clear_chat_history button
clear_history_button = ctk.CTkButton(
    sidebar_frame,
    text = "Clear chat history",
    command = clear_chat_history
)
clear_history_button.pack(pady=5)


#chat history heading
chat_history_label = ctk.CTkLabel(
    sidebar_frame,
    text="Chat History",
    font=("Roboto UI", 16, "bold")
)
chat_history_label.pack(
    pady=(15, 5)
)
#-----------------------
history_listbox = ctk.CTkTextbox(
    sidebar_frame,
    width=180,
    height=250,
    corner_radius=10
)

# for scrolling chat history in side frame
history_frame = ctk.CTkFrame(
    sidebar_frame
)

history_frame.pack(
    padx=10,
    pady=(0,10),
    fill="both"
)

history_listbox = ctk.CTkTextbox(
    history_frame,
    width=180,
    height=150
)

history_listbox.pack(
    side="left",
    fill="both",
    expand=True
)

history_scrollbar = ctk.CTkScrollbar(
    history_frame,
    command=history_listbox.yview
)

history_scrollbar.pack(
    side="right",
    fill="y"
)

history_listbox.configure(
    yscrollcommand=history_scrollbar.set
)


#refresh chat history function:
def refresh_chat_history():
    history_listbox.delete(
        "1.0",
         "end"
    )

    chat_files = sorted(
        os.listdir(CHATS_FOLDER),
        reverse=True
    )
    for file in chat_files:

        file_path = os.path.join(
            CHATS_FOLDER,
            file
        )

        try:

            with open(
                    file_path,
                    "r",
                    encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(data, dict):

                title = data.get(
                    "title",
                    file.replace(".json", "")
                )

            else:

                title = file.replace(
                    ".json",
                    ""
                )

            history_listbox.insert(
                "end",
                title + "\n"
            )

        except Exception as e:

            print(

                "History Error:",
                e
            )


# upload pdf_button
upload_button = ctk.CTkButton(
    sidebar_frame,
    text="Upload PDF",

    corner_radius=20,
    height=45,
    width=80,
    command=upload_pdf
)
upload_button.pack(
    pady=10,
    padx=20
)


# ====================================================
# NEW CHAT FUNCTION
# ==================================================== #

def new_chat():
    global messages
    global CURRENT_CHAT
    global CHAT_TITLE

    CURRENT_CHAT =None
    CHAT_TITLE = None

    messages = [
        {
            "role": "system",
            "content": "You are MemoMind AI"
        }
    ]

    chat_box.delete("1.0", "end")
    chat_box.insert("end", "Bot: Hello! How can I help you today?\n")

# ====================================================
# CLEAR MEMORY FUNCTION
# ==================================================== #

def clear_memory():
    global messages

    messages = [
        {
            "role": "system",
            "content": "You are MemoMind AI, a friendly AI assistant and Python tutor."
        }
    ]

    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)

    chat_box.delete("1.0", "end")

    memory_collection.delete(
        ids=memory_collection.get()["ids"]
    )


# ====================================================
# TEXT TO SPEECH FUNCTION
# ==================================================== #

# ====================================================
# SPEECH TO TEXT FUNCTION
# ==================================================== #

def listen_voice():
    stop_voice()
    recognizer = sr.Recognizer()

    try:

        typing_label.configure(text="Listening...")
        app.update()

        with sr.Microphone() as source:

            recognizer.adjust_for_ambient_noise(source)

            audio = recognizer.listen(source)

        user_text = recognizer.recognize_google(audio)

        typing_label.configure(text="")

        user_entry.delete(0, "end")

        user_entry.insert(0, user_text)

    except Exception as e:

        typing_label.configure(text="")

        chat_box.insert(
            "end",
            f"\nVoice Error:\n{str(e)}\n"
        )

        chat_box.see("end")


speech_queue = queue.Queue()


def stop_voice(event=None):
    global tts_engine
    try:
        tts_engine.stop()
    except:
        pass
    while not speech_queue.empty():
        speech_queue.get_nowait()


# stop speaking button
stop_button = ctk.CTkButton(
    sidebar_frame,
    text="🔇 Stop Speaking",
    corner_radius=20,
    height=45,
    width =80,
    command=stop_voice
)
stop_button.pack(
    pady=10,
    padx=20)
tts_engine = pyttsx3.init()
tts_engine.setProperty("rate", 170)


def speech_worker():
    global tts_engine

    while True:
        text = speech_queue.get()
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception as e:
            print("Speech Error:", str(e))


# without this audio wont play
threading.Thread(
    target=speech_worker,
    daemon=True
).start()

# ====================================================
# SIDEBAR BUTTONS
# ==================================================== #

new_chat_button = ctk.CTkButton(
    sidebar_frame,
    text="New Chat",
    corner_radius=20,
    height=45,
    width=80,
    command=new_chat

)
new_chat_button.pack(pady=(15,5), padx=20)

clear_button = ctk.CTkButton(
    sidebar_frame,
    text="Clear Memory",
    corner_radius=20,
    height=45,width=80,
    command=clear_memory
)
clear_button.pack(pady=10, padx=20)

# ====================================================
# STATUS LABEL
# ==================================================== #

status_label = ctk.CTkLabel(
    sidebar_frame,
    text=f"Model:\n{MODEL_NAME}",
    font=("Roboto ", 12),
    justify="left"
)
status_label.pack(side="bottom", pady=20)

# ====================================================
# MAIN FRAME
# ==================================================== #

main_frame = ctk.CTkFrame(app)
main_frame.pack(
    side="right",
    fill="both",
    expand=True
)

# ====================================================
# HEADER
# ==================================================== #

header_label = ctk.CTkLabel(
    main_frame,
    text="Welcome to MemoMind AI",
    font=("Roboto", 26, "bold")
)
header_label.pack(pady=15)

# ====================================================
# CHAT AREA
# ==================================================== #

chat_box = ctk.CTkTextbox(
    main_frame,
    wrap="word",
    font=("Roboto", 14),
    corner_radius=20
)

chat_box.pack(
    padx=20,
    pady=10,
    fill="both",
    expand=True
)

chat_box.insert(
    "end",
    "Bot: Hello! How can I help you today?\n"
)

# TYPING LABEL
typing_label = ctk.CTkLabel(
    main_frame,
    text="",
    font=("Roboto", 12)
)

typing_label.pack(pady=(0, 5))

# ====================================================
# INPUT FRAME
# ==================================================== #

input_frame = ctk.CTkFrame(
    main_frame,
    fg_color="transparent"
)

input_frame.pack(
    fill="x",
    padx=15,
    pady=15
)

# ====================================================
# USER INPUT
# ==================================================== #

user_entry = ctk.CTkEntry(
    input_frame,
    placeholder_text="Type your message...",
    height=40,
    corner_radius=25,
    font=("Roboto", 14)
)


# stop audio when enter is pressed
def entry_key(event):
    stop_voice()
    send_message()
user_entry.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(0, 10)
)
# stop audio when user starts typing
user_entry.bind("<Key>", stop_voice)


# ====================================================
# PDF DETECTION
# ====================================================

def is_pdf_request(user_input):
    pdf_keywords = [
        "pdf",
        "document",
        "uploaded file",
        "from the pdf",
        "from the document",
        "in the pdf",
        "in the document",
        "according to the pdf",
        "according to the document"
    ]

    user_input = user_input.lower()

    return any(
        keyword in user_input
        for keyword in pdf_keywords
    )


# WEB SEARCH
def web_search(query):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(
                    query,
                    max_results=5
            ):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", "")
                })

        return results
    except Exception as e:
        print("Web Search Error:", str(e))
        return []


# summary request

def is_summary_request(user_input):
    summary_keywords = [
        "summarize",
        "summary",
        "summarise",
        "give summary",
        "brief summary",
        "overview",
        "summarize pdf",
        "summarize document"
    ]

    user_input = user_input.lower()

    return any(
        keyword in user_input
        for keyword in summary_keywords
    )


# web search detector:
def is_web_search_requests(user_input):
    keywords = [
        "What is the latest update ",
        "Live updates",
        "latest",
        "today",
        "recent",
        "current",
        "news",
        "update",
        "weather",
        "stock",
        "price",
        "who won",
        "winner",
        "score",
        "match",
        "ipl",
        "cricket",
        "election",
        "live",
        "result",
        "study",
        "reports"
    ]
    user_input = user_input.lower()
    return any(
        keyword in user_input
        for keyword in keywords
    )
#smart_route route_query
def route_query(user_input):
    user_input = user_input.lower()
    if any(word in user_input for word in [
        "summarize the following text",
        "summarise the following text",
        "summarise this article",
        "summarize this article",
        "give me a 250 word summary",
        "create an overview of this content"
    ]):
        return "TEXT_SUMMARY"

    elif is_summary_request(user_input) and (
        "pdf" in user_input
        or "document" in user_input
        or "uploaded file" in user_input
    ):
        return "PDF_SUMMARY"

    elif is_pdf_request(user_input):
        return "PDF_QA"

    elif is_web_search_requests(user_input):
        return "WEB"


    elif any(word in user_input for word in [
        "remember",
        "what did i tell you",
        "do you remember",
        "my name",
        "Previous chat"
    ]):
        return "MEMORY"


    return "CHAT"


# ====================================================
# SEND MESSAGE FUNCTION
# ==================================================== #

def send_message():
    global messages
    global CURRENT_CHAT
    global CHAT_TITLE
    stop_voice()
    user_input = user_entry.get()

    if CURRENT_CHAT is None :
        CURRENT_CHAT =(
            f"chat_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        CHAT_TITLE =  user_input[:45]

    if user_input.strip() == "":
        return
    # ---------------- USER MESSAGE ---------------- #
    chat_box.insert(
        "end",
        f"\nYou:\n{user_input}\n"
    )
    chat_box.see("end")
    # ---------------- SAVE USER MESSAGE ---------------- #
    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )



    # ---------------- CLEAR ENTRY ---------------- #

    user_entry.delete(0, "end")

    # ---------------- SHOW TYPING ---------------- #

    typing_label.configure(text="AI is typing...")
    app.update()

    try:
        conversation = ""
        memory_context = ""
        # memory search
        if memory_collection.count() > 0:
            memory_embedding = embedding_model.encode(
                user_input
            ).tolist()
            memory_results = memory_collection.query(
                query_embeddings=[memory_embedding],
                n_results=5
            )
            memory_context = "\n".join(
                memory_results["documents"][0]
            )

        for msg in messages[-10:]:

            role = msg["role"]

            if role == "assistant":
                role = "AI"

            elif role == "user":
                role = "User"

            conversation += f"{role}: {msg['content']}\n"

        # ====================================================
        # PDF / NORMAL CHAT ROUTING
        # ====================================================

        context = ""
        sources = []
        citations = []
        route = route_query(user_input)

        print("\nROUTE =", route)
        # ---------- PDF SUMMARY ----------
        # if pdf summary
        # ====================================================
        # ROUTING SECTION
        # Replace your current:
        # if(...)
        # elif(...)
        # elif(...)
        # else(...)
        # block with this
        # ====================================================

        if route == "PDF_SUMMARY":

            print("PDF SUMMARY MODE")
            if collection.count() == 0:
                chat_box.insert(
                    "end",
                    "\nNo PDF uploaded yet.\n"
                )
                typing_label.configure(text="")
                return
            if CURRENT_PDF:
                all_data = collection.get(
                    where={"source": CURRENT_PDF}
                    )
            else:
                all_data = collection.get()

                documents = all_data["documents"]

                context = "\n".join(
                    documents[:18]
                )

            full_prompt = f"""
        You are MemoMind AI.

        Summarize the uploaded PDF.

        PDF Content:

        {context}

        Provide:
        1. Executive Summary
        2. Key Topics
        3. Important Concepts
        4. Conclusion
        """
        elif route == "PDF_QA":

            print("PDF QUESTION MODE")

            question_embedding = embedding_model.encode(
                user_input
            ).tolist()

            if CURRENT_PDF:

                print("Searching only in:", CURRENT_PDF)

                results = collection.query(
                    query_embeddings=[question_embedding],
                    n_results=10,
                    where={"source": CURRENT_PDF}
                )

            else:

                results = collection.query(
                    query_embeddings=[question_embedding],
                    n_results=10
                )

            retrieved_chunks = results["documents"][0]
            retrieved_sources = results["metadatas"][0]


            if not retrieved_chunks:
                chat_box.insert(
                    "end",
                    "\nNo relevant content found in the PDF.\n"
                )
                typing_label.configure(text="")
                return


            print("\nRetrieved Sources:")
            print(retrieved_sources)

            print("\nRetrieved Chunks:")
            for chunk in retrieved_chunks[:3]:
                print(chunk[:300])

            citations = []

            for item in retrieved_sources:
                citations.append(
                    f"{item['source']} (Page {item['page']})"
                )

            citations = list(set(citations))

            sources = list(
                set(
                    item["source"]
                    for item in retrieved_sources
                )
            )

            context = "\n".join(
                retrieved_chunks
            )

            full_prompt = f"""
        Relevant Memories:
        {memory_context}

        PDF Context:
        {context}

        User Question:
        {user_input}

        Instructions:
        - Answer only using the PDF context provided.
        - If the answer is not found in the PDF, say:
          "I could not find that information in the uploaded PDF."
        - Mention important details when available.
        - Be clear and concise.
        """

        elif route == "WEB":

            print("WEB SEARCH MODE")

            web_results = web_search(user_input)

            print("Results Found:", len(web_results))

            web_context = ""
            citations = []

            for item in web_results:
                web_context += f"""
        Title:
        {item['title']}

        Snippet:
        {item['snippet']}

        URL:
        {item['url']}
        """

                citations.append(item["url"])

            citations = list(set(citations))

            full_prompt = f"""
        Relevant Memories:
        {memory_context}

        Web Search Results:
        {web_context}

        User Question:
        {user_input}

        Instructions:
        - Answer using the web search results.
        - Prefer the search results over your internal knowledge.
        - If the answer is not available in the search results, clearly say so.
        - Include important facts from the search results.
        """
        elif route == "TEXT_SUMMARY":
            print("TEXT SUMMARY MODE")
            full_prompt = f"""
            Summarize the following text in 250 words.
            Text:
            {user_input}
            Provide:
            - Summary
            - Key Points
            - Important Keywords
            """
        elif route == "MEMORY":
            print("MEMORY MODE")
            full_prompt = f"""
            Relevant Memories:
            {memory_context}
            User Question:
            {user_input}

            Answer only from memories if possible.
            """

        else:

            print("NORMAL CHAT MODE")

            full_prompt = f"""
            Relevant Memories:
            {memory_context}

            Conversation History:
            {conversation}

            User:
            {user_input}

            Answer normally as a helpful AI assistant.
            """

        print("MODEL =", MODEL_NAME)
        print("PROMPT LENGTH =", len(full_prompt))



        messages_payload = [
            {
                "role": "system",
                "content": """
        You are MemoMind AI.

        You are a smart AI assistant.

        Rules:
        - Answer normally using your knowledge.
        - Use PDF content only when user explicitly asks about the uploaded document.
        - If user asks for PDF summary, summarize the uploaded PDF.
        - Be conversational and helpful.
        """
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ]
        # error handling for api key
        try:
            start_time = time.time()
            print(f"Using model: {MODEL_NAME}")
            # create empty response area
            chat_box.insert("end", "\nMemoMind AI:\n")
            chat_box.see("end")
            app.update()

            # before streamline starts
            typing_label.configure(
                text="Memomind is thinking..."
            )

            # start streaming
            bot_reply = ""
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages_payload,
                temperature=0.3,
                max_tokens=MAX_TOKENS,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    bot_reply = bot_reply + token
                    chat_box.insert("end", token)
                    chat_box.see("end")
                    app.update()

            # After stream completes
            typing_label.configure(
                text=""
            )
            elapsed = round(time.time() - start_time, 2)

            chat_box.insert(
                "end",
                f"\n\n⏱ Response time: {elapsed} sec\n"
            )
            chat_box.see("end")
        except Exception as e:

            print("Primary model failed:", e)

            try:

                response = client.chat.completions.create(
                    model=BACKUP_MODEL,
                    messages=messages_payload,
                    temperature=0.3,
                    max_tokens=MAX_TOKENS
                )

                bot_reply = response.choices[0].message.content
                chat_box.insert("end", bot_reply)
                chat_box.see("end")

            except Exception as backup_error:

                bot_reply = f"""
        Primary Model Error:
        {str(e)}

        Backup Model Error:
        {str(backup_error)}
        """
        # ------------

        speech_queue.put(bot_reply)

        # to check which model responded
        chat_box.insert(
            "end",
            f"\n\n🤖 Model Used: {MODEL_NAME}\n"
        )

        chat_box.see("end")
        # ---------------- API REQUEST ---------------- #

        # ---------------- REMOVE TYPING ---------------- #

        typing_label.configure(text="")

        # ---------------- DISPLAY BOT RESPONSE ---------------- #

        # show citation
        if citations:
            chat_box.insert(
                "end",
                f"\n📚 Citations:\n" +
                "\n".join(citations) +
                "\n"
            )
        chat_box.see("end")

        # ---------------- SPEAK RESPONSE ---------------- #

        # ---------------- STOP PREVIOUS SPEECH --------------#

        # ---------------- SPEAK RESPONSE ---------------- #

        # ---------------- SAVE ASSISTANT MESSAGE ---------------- #

        messages.append(
            {
                "role": "assistant",
                "content": bot_reply
            }
        )
        chat_data = {
            "title": CHAT_TITLE,
            "messages": messages
        }
        print("saving chat:", CURRENT_CHAT)
        print("Title:", CHAT_TITLE)
        with open(
                os.path.join(
                    CHATS_FOLDER,
                    CURRENT_CHAT
                ),
                "w",
                encoding="utf-8"
        ) as f:
            print("CURRENT_CHAT=", CURRENT_CHAT)
            print("CHAT_TITLE=", CHAT_TITLE)
            print("Savings:", chat_data)
            json.dump(
                chat_data,
                f,
                indent=4
            )

        refresh_chat_history()


        # tosave memories
        memory_text = f"""
        User: {user_input}

        AI: {bot_reply}
        """

        embedding = embedding_model.encode(
            memory_text
        ).tolist()

        memory_collection.add(
            ids=[str(memory_collection.count())],
            documents=[memory_text],
            embeddings=[embedding]
        )

        # Keep only latest 100 messages
        if len(messages) > 100:
            messages = messages[-100:]
        # save memory
        with open(CHAT_LOG, "a", encoding="utf-8") as f:
            f.write(f"\nUser: {user_input}\n")
            f.write(f"AI: {bot_reply}\n")
            f.write("-" * 50 + "\n")

        # to show memory
        chat_box.insert(
            "end",
            f"\n🧠 Memory Entries: {memory_collection.count()}\n"
        )

        chat_box.see("end")
        # to save chat memory

    except Exception as e:

        typing_label.configure(text="")

        chat_box.insert(
            "end",
            f"\nError:\n{str(e)}\n"
    )
    chat_box.see("end")

# ====================================================
# SEND BUTTON
# ==================================================== #
send_button = ctk.CTkButton(
    input_frame,
    text="Send",
    height=45,
    corner_radius=25,
    font=("Roboto UI", 14, "bold"),
    command=send_message
)

send_button.pack(side="right")

# ====================================================
# MICROPHONE BUTTON
# ==================================================== #

mic_button = ctk.CTkButton(
    input_frame,
    text="🎤",
    width=55,
    height=45,
    corner_radius=25,
    command=listen_voice
)
mic_button.pack(side="right", padx=(10, 5))
refresh_chat_history()

# ENTER KEY SUPPORT
def enter_key(event):
    stop_voice()
    send_message()


app.bind("<Return>", enter_key)
# RUN APP
app.mainloop()

"go through the code and let me know what are the errors currently working on citation, it was working only once when a project deployed "