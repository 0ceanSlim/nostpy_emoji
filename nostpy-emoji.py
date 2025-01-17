import asyncio
import csv
import json
import os
from tkinter import BOTH, filedialog, messagebox
import yaml
from websockets import connect
from pynostr.key import PrivateKey
from pynostr.event import Event
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

# Load config
CONFIG_FILE = "config.yml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Config file '{CONFIG_FILE}' not found.")
    with open(CONFIG_FILE, 'r') as file:
        return yaml.safe_load(file)

config = load_config()
PRIVATE_KEY = config["private_key"]
RELAYS = config["relays"]

# Generate public key from private key
private_key = PrivateKey(bytes.fromhex(PRIVATE_KEY))
PUBLIC_KEY = private_key.public_key.hex()

def read_emoji_data(csv_file):
    emoji_data = []
    with open(csv_file, 'r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            emoji_data.append({"name": row[0], "image_url": row[1]})
    return emoji_data

def create_event(emoji_data, set_name):
    tags = [["d", set_name], ["title", set_name]]
    for emoji in emoji_data:
        tags.append(["emoji", emoji["name"], emoji["image_url"]])
    
    event = Event(
        kind=30030,
        content="",
        tags=tags,
        pubkey=PUBLIC_KEY
    )
    return event

def sign_event(evt):
    evt.sign(PRIVATE_KEY)
    return evt

async def send_event(relay_url, event, response_box):
    try:
        async with connect(relay_url) as websocket:
            event_dict = {
                "id": event.id,
                "pubkey": event.pubkey,
                "created_at": event.created_at,
                "kind": event.kind,
                "tags": event.tags,
                "content": event.content,
                "sig": event.sig
            }
            await websocket.send(json.dumps(["EVENT", event_dict]))
            response = await websocket.recv()
            response_box.insert(tk.END, f"Relay {relay_url} response: {response}\n")
    except Exception as e:
        response_box.insert(tk.END, f"Error sending to {relay_url}: {e}\n")

async def send_to_all_relays(emoji_data, set_name, response_box):
    event = create_event(emoji_data, set_name)
    signed_event = sign_event(event)
    tasks = [send_event(relay, signed_event, response_box) for relay in RELAYS]
    await asyncio.gather(*tasks)

def browse_csv(entry):
    file_path = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

def on_send(csv_entry, set_name_entry, response_box):
    csv_file = csv_entry.get()
    set_name = set_name_entry.get()

    if not csv_file or not set_name:
        messagebox.showerror("Input Error", "Please provide a CSV file and set name.")
        return

    try:
        emoji_data = read_emoji_data(csv_file)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV file: {e}")
        return

    response_box.delete(1.0, tk.END)
    asyncio.run(send_to_all_relays(emoji_data, set_name, response_box))

# GUI
def create_gui():
    # Use ttkbootstrap for modern styling with dark theme
    app = tb.Window(themename="darkly")
    app.title("Nostr Emoji Event Sender")
    app.geometry("600x400")
    
    # Change the application icon
    icon = Image.open("icon.png")  # Replace with your icon path
    photo = ImageTk.PhotoImage(icon)
    app.iconphoto(False, photo)

    # Create a main frame
    main_frame = tb.Frame(app)
    main_frame.pack(fill=BOTH, expand=YES, padx=20, pady=20)

    # Configure grid
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(4, weight=1)

    # CSV File Input
    tb.Label(main_frame, text="CSV File:", bootstyle="info").grid(row=0, column=0, padx=(0,10), pady=10, sticky=W)
    csv_entry = tb.Entry(main_frame)
    csv_entry.grid(row=0, column=1, padx=(0,10), pady=10, sticky=EW)
    tb.Button(main_frame, text="Browse", bootstyle="secondary", command=lambda: browse_csv(csv_entry)).grid(row=0, column=2, pady=10, sticky=E)

    # Set Name Input
    tb.Label(main_frame, text="Set Name:", bootstyle="info").grid(row=1, column=0, padx=(0,10), pady=10, sticky=W)
    set_name_entry = tb.Entry(main_frame)
    set_name_entry.grid(row=1, column=1, columnspan=2, padx=(0,10), pady=10, sticky=EW)

    # Send Button
    send_button = tb.Button(
        main_frame, text="Send", bootstyle="success", command=lambda: on_send(csv_entry, set_name_entry, response_box)
    )
    send_button.grid(row=2, column=0, columnspan=3, pady=15, sticky=EW)

    # Response Box
    tb.Label(main_frame, text="Responses:", bootstyle="info").grid(row=3, column=0, padx=(0,10), pady=(10,5), sticky=W)
    response_box = ScrolledText(main_frame, wrap=tk.WORD, height=10, background="#2b2b2b", foreground="#ffffff", insertbackground="white")
    response_box.grid(row=4, column=0, columnspan=3, pady=(0,10), sticky=NSEW)

    app.mainloop()

if __name__ == "__main__":
    create_gui()
