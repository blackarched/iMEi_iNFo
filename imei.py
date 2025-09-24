import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import json

# Define the API key and endpoint (replace with actual API details)
API_KEY = 'your_api_key_here'
API_ENDPOINT = 'https://api.imei.info/'

def get_imei_info(imei):
    url = f"{API_ENDPOINT}?imei={imei}&key={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {e}")
        return None

def validate_imei(imei):
    if not imei or not imei.isdigit() or len(imei) != 15:
        return False
    return True

def display_imei_info():
    imei = imei_entry.get()
    if not validate_imei(imei):
        messagebox.showerror("Error", "Please enter a valid 15-digit IMEI number.")
        return

    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, "Retrieving information... Please wait.\n")
    submit_button.config(state=tk.DISABLED)

    def fetch_info():
        info = get_imei_info(imei)
        if info:
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"Network Status: {info.get('network', 'N/A')}\n")
            result_text.insert(tk.END, f"Unlock Status: {info.get('unlock_status', 'N/A')}\n")
            result_text.insert(tk.END, f"Stolen Check: {info.get('stolen', 'N/A')}\n")
            result_text.insert(tk.END, f"Brand: {info.get('brand', 'N/A')}\n")
            result_text.insert(tk.END, f"Model: {info.get('model', 'N/A')}\n")
            result_text.insert(tk.END, f"Country: {info.get('country', 'N/A')}\n")
            result_text.insert(tk.END, f"Carrier: {info.get('carrier', 'N/A')}\n")
            result_text.insert(tk.END, f"IMEI Type: {info.get('type', 'N/A')}\n")
            result_text.insert(tk.END, f"Reported Lost: {info.get('lost', 'N/A')}\n")
            result_text.insert(tk.END, f"Reported Damaged: {info.get('damaged', 'N/A')}\n")
            result_text.insert(tk.END, f"Warranty Status: {info.get('warranty', 'N/A')}\n")
        else:
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, "Failed to retrieve IMEI information. Please try again later.\n")
        submit_button.config(state=tk.NORMAL)

    threading.Thread(target=fetch_info).start()

# Create the main window
root = tk.Tk()
root.title("Advanced IMEI Info Tool")
root.configure(bg='#000000')

# Create and place widgets
imei_label = ttk.Label(root, text="Enter IMEI Number:", background='#000000', foreground='#00FF00', font=('Arial', 12))
imei_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')

imei_entry = ttk.Entry(root, font=('Arial', 12))
imei_entry.grid(row=0, column=1, padx=10, pady=10)

submit_button = ttk.Button(root, text="Submit", command=display_imei_info, style='TButton')
submit_button.grid(row=0, column=2, padx=10, pady=10)

result_text = tk.Text(root, bg='#000000', fg='#00FF00', font=('Arial', 12), height=20, width=80)
result_text.grid(row=1, column=0, columnspan=3, padx=10, pady=10)

# Configure the style
style = ttk.Style()
style.configure("TButton", background='#FF00FF', foreground='#000000', font=('Arial', 12))
style.configure("TLabel", background='#000000', foreground='#00FF00', font=('Arial', 12))
style.configure("TEntry", fieldbackground='#000000', foreground='#00FF00', font=('Arial', 12))

# Run the application
root.mainloop()