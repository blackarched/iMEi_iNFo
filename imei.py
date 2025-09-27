import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
import json

# Define multiple API configurations for fallback support
API_CONFIGS = [
    {
        'name': 'IMEI.info',
        'endpoint': 'https://imei.info/api/v1/imei-check',
        'key': 'your_api_key_here',
        'format': lambda imei, key, endpoint: f"{endpoint}?imei={imei}&token={key}"
    },
    {
        'name': 'IMEIpro',
        'endpoint': 'https://imeipro.info/api',
        'key': 'your_imeipro_key_here',
        'format': lambda imei, key, endpoint: f"{endpoint}/check?imei={imei}&key={key}"
    },
    {
        'name': 'DeviceAtlas',
        'endpoint': 'https://deviceatlas.com/api/imei',
        'key': 'your_deviceatlas_key_here',
        'format': lambda imei, key, endpoint: f"{endpoint}/{imei}?key={key}"
    }
]

# Fallback configuration for backward compatibility
API_KEY = 'your_api_key_here'
API_ENDPOINT = 'https://api.imei.info/'

def get_imei_info(imei):
    """Try multiple API sources with fallback support"""
    errors = []
    
    # Try each configured API
    for config in API_CONFIGS:
        if config['key'] == 'your_api_key_here' or config['key'].startswith('your_'):
            continue  # Skip unconfigured APIs
        
        try:
            url = config['format'](imei, config['key'], config['endpoint'])
            print(f"Trying {config['name']} API...")
            
            headers = {
                'User-Agent': 'IMEI-Tool-Python/1.0',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API-specific error formats
            if 'errors' in data and data['errors']:
                raise requests.exceptions.RequestException(f"API Error: {data['errors'][0].get('message', 'Unknown error')}")
            
            # Add metadata
            data['api_source'] = config['name']
            data['query_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"Successfully retrieved data from {config['name']}")
            return data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"{config['name']}: {str(e)}"
            print(f"API Request failed for {config['name']}: {e}")
            errors.append(error_msg)
            continue
    
    # Try fallback endpoint
    try:
        print("Trying fallback API...")
        url = f"{API_ENDPOINT}?imei={imei}&key={API_KEY}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        data['api_source'] = 'Fallback API'
        data['query_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        return data
        
    except requests.exceptions.RequestException as e:
        errors.append(f"Fallback API: {str(e)}")
    
    # If all APIs fail, return None with error info
    print(f"All API sources failed. Errors: {'; '.join(errors)}")
    return None

def test_api_connectivity():
    """Test connectivity to all configured API endpoints"""
    results = []
    
    for config in API_CONFIGS:
        if config['key'].startswith('your_'):
            results.append({
                'name': config['name'],
                'status': 'Not Configured',
                'message': 'API key not set'
            })
            continue
        
        try:
            response = requests.head(config['endpoint'], timeout=5)
            results.append({
                'name': config['name'],
                'status': 'Online' if response.ok else 'Error',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            })
        except requests.exceptions.RequestException as e:
            results.append({
                'name': config['name'],
                'status': 'Offline',
                'error': str(e)
            })
    
    return results

def validate_imei(imei):
    """Validate IMEI using Luhn algorithm"""
    if not imei or len(imei) != 15 or not imei.isdigit():
        return False
    
    # Check for common invalid patterns
    if imei == '000000000000000' or imei == '111111111111111':
        return False
    if len(set(imei)) == 1:  # All same digits
        return False
    
    # Luhn algorithm validation
    sum_digits = 0
    alternate = False
    
    for i in range(len(imei) - 1, -1, -1):
        n = int(imei[i])
        
        if alternate:
            n *= 2
            if n > 9:
                n = (n % 10) + 1
        
        sum_digits += n
        alternate = not alternate
    
    return (sum_digits % 10) == 0

def format_imei(imei):
    """Clean and format IMEI input"""
    if not imei:
        return None
    
    # Remove spaces, hyphens, and other non-digit characters
    cleaned = ''.join(filter(str.isdigit, imei))
    
    # Check length
    if len(cleaned) != 15:
        return None
    
    return cleaned

def get_tac_info(imei):
    """Get device information from TAC (first 8 digits)"""
    tac = imei[:8]
    tac_database = {
        '35209900': {'brand': 'Apple', 'model': 'iPhone', 'type': 'Smartphone'},
        '35216406': {'brand': 'Samsung', 'model': 'Galaxy', 'type': 'Smartphone'},
        '35328504': {'brand': 'Nokia', 'model': 'Nokia Phone', 'type': 'Feature Phone'},
        '35875505': {'brand': 'Huawei', 'model': 'Mate/P Series', 'type': 'Smartphone'},
        '35699302': {'brand': 'Xiaomi', 'model': 'Mi/Redmi', 'type': 'Smartphone'},
        '35841605': {'brand': 'OnePlus', 'model': 'OnePlus', 'type': 'Smartphone'},
        '35404907': {'brand': 'Google', 'model': 'Pixel', 'type': 'Smartphone'},
        '35161102': {'brand': 'LG', 'model': 'LG Phone', 'type': 'Smartphone'},
        '35434505': {'brand': 'Sony', 'model': 'Xperia', 'type': 'Smartphone'},
        '35291508': {'brand': 'Motorola', 'model': 'Moto', 'type': 'Smartphone'}
    }
    
    return tac_database.get(tac, {'brand': 'Unknown', 'model': 'Unknown', 'type': 'Unknown'})

def display_imei_info():
    imei_raw = imei_entry.get().strip()
    
    # Format and validate IMEI
    imei = format_imei(imei_raw)
    if not imei:
        messagebox.showerror("Error", "Invalid IMEI format. Please enter a valid 15-digit IMEI number.")
        return
    
    if not validate_imei(imei):
        messagebox.showerror("Error", "Invalid IMEI checksum. Please verify the IMEI number.")
        return
    
    # Update entry with cleaned IMEI
    imei_entry.delete(0, tk.END)
    imei_entry.insert(0, imei)

    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, "Retrieving information... Please wait.\n")
    submit_button.config(state=tk.DISABLED)

    def fetch_info():
        # Get offline TAC information first
        tac_info = get_tac_info(imei)
        
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "=== IMEI ANALYSIS REPORT ===\n\n")
        result_text.insert(tk.END, f"IMEI: {imei}\n")
        result_text.insert(tk.END, f"TAC (Type Allocation Code): {imei[:8]}\n")
        result_text.insert(tk.END, f"FAC (Final Assembly Code): {imei[8:10]}\n")
        result_text.insert(tk.END, f"SNR (Serial Number): {imei[10:14]}\n")
        result_text.insert(tk.END, f"Check Digit: {imei[14]}\n\n")
        
        result_text.insert(tk.END, "=== DEVICE INFORMATION (TAC Database) ===\n")
        result_text.insert(tk.END, f"Brand: {tac_info['brand']}\n")
        result_text.insert(tk.END, f"Model: {tac_info['model']}\n")
        result_text.insert(tk.END, f"Type: {tac_info['type']}\n\n")
        
        # Try to get online information
        info = get_imei_info(imei)
        if info:
            result_text.insert(tk.END, "=== ONLINE DATABASE INFORMATION ===\n")
            result_text.insert(tk.END, f"Network Status: {info.get('network', 'N/A')}\n")
            result_text.insert(tk.END, f"Unlock Status: {info.get('unlock_status', 'N/A')}\n")
            result_text.insert(tk.END, f"Stolen Check: {info.get('stolen', 'N/A')}\n")
            result_text.insert(tk.END, f"Brand (Online): {info.get('brand', 'N/A')}\n")
            result_text.insert(tk.END, f"Model (Online): {info.get('model', 'N/A')}\n")
            result_text.insert(tk.END, f"Country: {info.get('country', 'N/A')}\n")
            result_text.insert(tk.END, f"Carrier: {info.get('carrier', 'N/A')}\n")
            result_text.insert(tk.END, f"IMEI Type: {info.get('type', 'N/A')}\n")
            result_text.insert(tk.END, f"Reported Lost: {info.get('lost', 'N/A')}\n")
            result_text.insert(tk.END, f"Reported Damaged: {info.get('damaged', 'N/A')}\n")
            result_text.insert(tk.END, f"Warranty Status: {info.get('warranty', 'N/A')}\n")
        else:
            result_text.insert(tk.END, "=== ONLINE DATABASE ===\n")
            result_text.insert(tk.END, "Failed to retrieve online IMEI information.\n")
            result_text.insert(tk.END, "This may be due to API limitations or network issues.\n")
        
        submit_button.config(state=tk.NORMAL)

    threading.Thread(target=fetch_info).start()

def process_batch_imeis():
    """Process multiple IMEIs from batch input"""
    batch_input = batch_text.get(1.0, tk.END).strip()
    
    if not batch_input or batch_input == "Enter multiple IMEIs (one per line):":
        messagebox.showerror("Error", "Please enter IMEIs for batch processing.")
        return
    
    # Parse IMEIs from input
    lines = batch_input.split('\n')
    imeis = []
    
    for line in lines:
        line = line.strip()
        if line and line != "Enter multiple IMEIs (one per line):":
            # Handle comma-separated values on same line
            if ',' in line:
                imeis.extend([imei.strip() for imei in line.split(',') if imei.strip()])
            else:
                imeis.append(line)
    
    if not imeis:
        messagebox.showerror("Error", "No valid IMEIs found in input.")
        return
    
    # Clean and validate IMEIs
    valid_imeis = []
    invalid_imeis = []
    
    for imei in imeis:
        cleaned = format_imei(imei)
        if cleaned and validate_imei(cleaned):
            valid_imeis.append(cleaned)
        else:
            invalid_imeis.append(imei)
    
    if invalid_imeis:
        if not messagebox.askyesno("Invalid IMEIs Found", 
                                 f"Found {len(invalid_imeis)} invalid IMEIs: {', '.join(invalid_imeis[:5])}{'...' if len(invalid_imeis) > 5 else ''}\n\n"
                                 f"Continue processing {len(valid_imeis)} valid IMEIs?"):
            return
    
    if not valid_imeis:
        messagebox.showerror("Error", "No valid IMEIs to process.")
        return
    
    if len(valid_imeis) > 10:
        if not messagebox.askyesno("Large Batch", 
                                 f"You are about to process {len(valid_imeis)} IMEIs.\n"
                                 f"This may take some time and consume API quota.\n\nContinue?"):
            return
    
    # Start batch processing in separate thread
    batch_button.config(state=tk.DISABLED, text="Processing...")
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, f"Starting batch processing of {len(valid_imeis)} IMEIs...\n\n")
    
    def batch_worker():
        results = []
        errors = []
        
        for i, imei in enumerate(valid_imeis, 1):
            try:
                result_text.insert(tk.END, f"[{i}/{len(valid_imeis)}] Processing {imei}...\n")
                result_text.see(tk.END)
                root.update()
                
                # Add delay to respect API rate limits
                if i > 1:
                    time.sleep(1)
                
                # Get TAC info first (always available)
                tac_info = get_tac_info(imei)
                
                # Try to get online info
                online_info = get_imei_info(imei)
                
                result = {
                    'imei': imei,
                    'tac_info': tac_info,
                    'online_info': online_info,
                    'status': 'success' if online_info else 'partial'
                }
                
                results.append(result)
                
                result_text.insert(tk.END, f"✓ {imei}: {tac_info['brand']} {tac_info['model']}\n")
                
                if online_info:
                    result_text.insert(tk.END, f"  Online: {online_info.get('api_source', 'API')}\n")
                else:
                    result_text.insert(tk.END, f"  Online: Failed (using offline data)\n")
                
                result_text.insert(tk.END, "\n")
                
            except Exception as e:
                error_msg = f"Error processing {imei}: {str(e)}"
                errors.append({'imei': imei, 'error': str(e)})
                result_text.insert(tk.END, f"✗ {error_msg}\n\n")
                print(error_msg)
            
            result_text.see(tk.END)
            root.update()
        
        # Display summary
        display_batch_summary(results, errors)
        
        batch_button.config(state=tk.NORMAL, text="Process Batch")
        
        # Offer to save results
        if messagebox.askyesno("Save Results", "Would you like to save the batch results to a file?"):
            save_batch_results(results, errors)
    
    threading.Thread(target=batch_worker).start()

def display_batch_summary(results, errors):
    """Display batch processing summary"""
    result_text.insert(tk.END, "\n" + "="*60 + "\n")
    result_text.insert(tk.END, "BATCH PROCESSING SUMMARY\n")
    result_text.insert(tk.END, "="*60 + "\n\n")
    
    successful = len([r for r in results if r['status'] == 'success'])
    partial = len([r for r in results if r['status'] == 'partial'])
    failed = len(errors)
    total = len(results) + failed
    
    result_text.insert(tk.END, f"Total IMEIs processed: {total}\n")
    result_text.insert(tk.END, f"Successful (with online data): {successful}\n")
    result_text.insert(tk.END, f"Partial (offline data only): {partial}\n")
    result_text.insert(tk.END, f"Failed: {failed}\n\n")
    
    if errors:
        result_text.insert(tk.END, "ERRORS:\n")
        for error in errors:
            result_text.insert(tk.END, f"- {error['imei']}: {error['error']}\n")
        result_text.insert(tk.END, "\n")
    
    result_text.insert(tk.END, "DEVICE SUMMARY:\n")
    brand_count = {}
    for result in results:
        brand = result['tac_info']['brand']
        brand_count[brand] = brand_count.get(brand, 0) + 1
    
    for brand, count in sorted(brand_count.items()):
        result_text.insert(tk.END, f"- {brand}: {count} device(s)\n")
    
    result_text.see(tk.END)

def save_batch_results(results, errors):
    """Save batch results to CSV file"""
    try:
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Batch Results"
        )
        
        if not filename:
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['IMEI', 'Status', 'Brand', 'Model', 'Type', 'TAC', 'API_Source', 'Network_Status', 'Error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for result in results:
                tac_info = result['tac_info']
                online_info = result['online_info'] or {}
                
                writer.writerow({
                    'IMEI': result['imei'],
                    'Status': result['status'],
                    'Brand': tac_info['brand'],
                    'Model': tac_info['model'],
                    'Type': tac_info['type'],
                    'TAC': result['imei'][:8],
                    'API_Source': online_info.get('api_source', 'N/A'),
                    'Network_Status': online_info.get('network', 'N/A'),
                    'Error': ''
                })
            
            for error in errors:
                writer.writerow({
                    'IMEI': error['imei'],
                    'Status': 'failed',
                    'Brand': 'N/A',
                    'Model': 'N/A',
                    'Type': 'N/A',
                    'TAC': error['imei'][:8] if len(error['imei']) >= 8 else 'N/A',
                    'API_Source': 'N/A',
                    'Network_Status': 'N/A',
                    'Error': error['error']
                })
        
        messagebox.showinfo("Success", f"Batch results saved to {filename}")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save results: {str(e)}")

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

# Batch processing section
batch_label = ttk.Label(root, text="Batch Processing:", background='#000000', foreground='#00FF00', font=('Arial', 12))
batch_label.grid(row=2, column=0, padx=10, pady=10, sticky='w')

batch_text = tk.Text(root, bg='#000000', fg='#00FF00', font=('Arial', 10), height=5, width=60)
batch_text.grid(row=3, column=0, columnspan=3, padx=10, pady=5)
batch_text.insert(tk.END, "Enter multiple IMEIs (one per line):\n")

batch_button = ttk.Button(root, text="Process Batch", command=lambda: process_batch_imeis(), style='TButton')
batch_button.grid(row=4, column=1, padx=10, pady=10)

result_text = tk.Text(root, bg='#000000', fg='#00FF00', font=('Arial', 12), height=20, width=80)
result_text.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

# Configure the style
style = ttk.Style()
style.configure("TButton", background='#FF00FF', foreground='#000000', font=('Arial', 12))
style.configure("TLabel", background='#000000', foreground='#00FF00', font=('Arial', 12))
style.configure("TEntry", fieldbackground='#000000', foreground='#00FF00', font=('Arial', 12))

# Run the application
root.mainloop()