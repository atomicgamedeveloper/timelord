import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, time
import os
import tempfile
import json
import threading
import time as time_module

def calculate_time_sum(time_list, target_hours=10):
    """
    Calculate the sum of time periods from a list of time ranges.
    
    Args:
        time_list (list): List of strings representing time periods (e.g. "5:00 - 8:05am")
        target_hours (float): Target hours to reach
        
    Returns:
        tuple: (total_time_str, remaining_time_str, total_minutes, remaining_minutes)
    """
    total_minutes = 0
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_period = 'am' if current_hour < 12 else 'pm'
    
    for time_range in time_list:
        # Skip empty entries
        if not time_range.strip():
            continue
            
        # Clean up the input
        time_range = time_range.strip().replace('–', '-')
        
        # Check if this is a negative time entry
        is_negative = time_range.startswith('-')
        if is_negative:
            time_range = time_range[1:].strip()
        
        # Check for open-ended time (no end time specified)
        open_ended_match = re.search(r'(\d+):?(\d*)(?:\s*(?:am|pm))?\s*[-–]\s*$', time_range)
        if open_ended_match:
            # Extract start time
            start_hour, start_min = open_ended_match.groups()
            start_min = start_min if start_min else '00'
            
            # Extract am/pm designation for start time
            start_ampm_match = re.search(r'(\d+):?(\d*)\s*(am|pm)', time_range.lower())
            start_period = start_ampm_match.group(3) if start_ampm_match else current_period
            
            # Convert start time to 24-hour format
            start_hour = int(start_hour)
            start_min = int(start_min)
            
            if start_period == 'pm' and start_hour != 12:
                start_hour += 12
            if start_period == 'am' and start_hour == 12:
                start_hour = 0
            
            # Calculate duration from start time to now
            start_minutes = start_hour * 60 + start_min
            current_minutes = current_hour * 60 + current_minute
            
            # Handle case where start time is later in the day than current time
            if current_minutes < start_minutes:
                current_minutes += 24 * 60
            
            duration = current_minutes - start_minutes
            
            if is_negative:
                duration = -duration
            
            total_minutes += duration
            continue
        
        # Regular time range parsing
        match = re.search(r'(\d+):?(\d*)(?:\s*(?:am|pm))?\s*-\s*(\d+):?(\d*)(?:\s*(?:am|pm))?', time_range)
        if not match:
            continue
            
        start_hour, start_min, end_hour, end_min = match.groups()
        
        # Handle empty minute values
        start_min = start_min if start_min else '00'
        end_min = end_min if end_min else '00'
        
        # Extract am/pm designations
        start_ampm = re.search(r'(\d+):?(\d*)\s*(am|pm)', time_range.lower())
        end_ampm = re.search(r'-\s*(\d+):?(\d*)\s*(am|pm)', time_range.lower())
        
        # Set default to AM if not specified
        start_period = start_ampm.group(3) if start_ampm else 'am'
        end_period = end_ampm.group(3) if end_ampm else 'am'
        
        # Create datetime objects for start and end times
        start_hour = int(start_hour)
        start_min = int(start_min)
        end_hour = int(end_hour)
        end_min = int(end_min)
        
        # Adjust for 12-hour clock
        if start_period == 'pm' and start_hour != 12:
            start_hour += 12
        if start_period == 'am' and start_hour == 12:
            start_hour = 0
            
        if end_period == 'pm' and end_hour != 12:
            end_hour += 12
        if end_period == 'am' and end_hour == 12:
            end_hour = 0
        
        # Calculate duration in minutes
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Handle overnight ranges
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
            
        duration = end_minutes - start_minutes
        
        if is_negative:
            duration = -duration
            
        total_minutes += duration
    
    # Convert total minutes to hours and minutes
    hours, minutes = divmod(abs(total_minutes), 60)
    sign = "-" if total_minutes < 0 else ""
    total_time_str = f"{sign}{hours} hours and {minutes} minutes"
    
    # Calculate remaining time to reach target
    target_minutes = target_hours * 60
    remaining_minutes = target_minutes - total_minutes
    
    if remaining_minutes > 0:
        rem_hours, rem_mins = divmod(remaining_minutes, 60)
        remaining_time_str = f"{rem_hours} hours and {rem_mins} minutes remaining"
    elif remaining_minutes == 0:
        remaining_time_str = "Target reached!"
    else:
        over_hours, over_mins = divmod(abs(remaining_minutes), 60)
        remaining_time_str = f"Target exceeded by {over_hours} hours and {over_mins} minutes"
    
    return total_time_str, remaining_time_str, total_minutes, remaining_minutes

class TimeCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Time Period Calculator")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Auto-update variables
        self.auto_update_enabled = tk.BooleanVar(value=True)
        self.update_interval = 30  # seconds
        self.update_thread = None
        self.running = True
        self.last_remaining_minutes = None
        self.target_reached_notified = False
        
        # Set up temporary save file path
        self.temp_dir = tempfile.gettempdir()
        self.temp_file = os.path.join(self.temp_dir, "time_calculator_temp.json")
        
        # Set style
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat")
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        style.configure("Success.TLabel", foreground="green", font=("Arial", 10, "bold"))
        style.configure("Warning.TLabel", foreground="red", font=("Arial", 10, "bold"))
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header
        header_label = ttk.Label(self.main_frame, text="Enhanced Time Period Calculator", style="Header.TLabel")
        header_label.pack(pady=(0, 10))
        
        instruction_label = ttk.Label(self.main_frame, 
            text="Enter time periods (one per line)\nExamples: '5:00 - 8:05am', '-2:00 - 3:00pm' (negative), '9:45 –' (open-ended)")
        instruction_label.pack(pady=(0, 5), anchor="w")
        
        # Create settings frame
        self.settings_frame = ttk.LabelFrame(self.main_frame, text="Settings", padding="5")
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        # Target hours setting
        self.target_frame = ttk.Frame(self.settings_frame)
        self.target_frame.pack(fill=tk.X, pady=2)
        
        target_label = ttk.Label(self.target_frame, text="Target hours:")
        target_label.pack(side=tk.LEFT, padx=5)
        
        self.target_var = tk.StringVar(value="10")
        self.target_entry = ttk.Entry(self.target_frame, textvariable=self.target_var, width=10)
        self.target_entry.pack(side=tk.LEFT, padx=5)
        
        # Auto-update settings
        self.auto_update_frame = ttk.Frame(self.settings_frame)
        self.auto_update_frame.pack(fill=tk.X, pady=2)
        
        self.auto_update_checkbox = ttk.Checkbutton(
            self.auto_update_frame, 
            text="Auto-update every 30 seconds", 
            variable=self.auto_update_enabled,
            command=self.toggle_auto_update
        )
        self.auto_update_checkbox.pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        self.status_var = tk.StringVar(value="●")
        self.status_label = ttk.Label(self.auto_update_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Create text area for input
        self.input_frame = ttk.Frame(self.main_frame)
        self.input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.input_text = tk.Text(self.input_frame, height=12, width=50)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        self.scrollbar = ttk.Scrollbar(self.input_frame, command=self.input_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_text.config(yscrollcommand=self.scrollbar.set)
        
        # Add example button
        self.example_button = ttk.Button(self.main_frame, text="Load Example", command=self.load_example)
        self.example_button.pack(pady=5, anchor="w")
        
        # Create button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        # Add buttons
        self.calculate_button = ttk.Button(self.button_frame, text="Calculate Now", command=self.calculate)
        self.calculate_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(self.button_frame, text="Clear", command=self.clear)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Create result frame
        self.result_frame = ttk.LabelFrame(self.main_frame, text="Results", padding="5")
        self.result_frame.pack(fill=tk.X, pady=5)
        
        # Last updated label
        self.last_updated_var = tk.StringVar()
        self.last_updated_label = ttk.Label(self.result_frame, textvariable=self.last_updated_var, font=("Arial", 8))
        self.last_updated_label.pack(anchor="w", pady=2)
        
        result_label = ttk.Label(self.result_frame, text="Total time:")
        result_label.pack(anchor="w", pady=2)
        
        self.result_var = tk.StringVar()
        self.result_var.set("0 hours and 0 minutes")
        self.result_display = ttk.Label(self.result_frame, textvariable=self.result_var, font=("Arial", 10, "bold"))
        self.result_display.pack(anchor="w", pady=2)
        
        # Create remaining time frame
        self.remaining_var = tk.StringVar()
        self.remaining_var.set("")
        self.remaining_display = ttk.Label(self.result_frame, textvariable=self.remaining_var, font=("Arial", 10, "bold"))
        self.remaining_display.pack(anchor="w", pady=2)
        
        # Load saved data on startup
        self.load_temp_data()
        
        # Bind events for auto-saving
        self.input_text.bind('<KeyRelease>', self.auto_save)
        self.target_var.trace('w', self.auto_save)
        
        # Start auto-update thread
        self.start_auto_update()
        
        # Save on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def start_auto_update(self):
        """Start the auto-update thread"""
        if self.auto_update_enabled.get():
            self.update_thread = threading.Thread(target=self.auto_update_loop, daemon=True)
            self.update_thread.start()
    
    def auto_update_loop(self):
        """Main auto-update loop running in background thread"""
        while self.running:
            if self.auto_update_enabled.get():
                # Schedule calculation on main thread
                self.root.after(0, self.calculate_auto)
                
                # Update status indicator
                self.root.after(0, lambda: self.status_var.set("● Updated"))
                self.root.after(1000, lambda: self.status_var.set("●"))
            
            # Wait for update interval
            for _ in range(self.update_interval):
                if not self.running:
                    break
                time_module.sleep(1)
    
    def toggle_auto_update(self):
        """Toggle auto-update on/off"""
        if self.auto_update_enabled.get():
            if not self.update_thread or not self.update_thread.is_alive():
                self.start_auto_update()
            self.status_label.config(foreground="green")
        else:
            self.status_label.config(foreground="gray")
    
    def calculate_auto(self):
        """Calculate automatically (called by auto-update thread)"""
        self.calculate(silent=True)
    
    def show_target_reached_popup(self, remaining_minutes):
        """Show popup notification when target is reached"""
        if remaining_minutes <= 0 and not self.target_reached_notified:
            self.target_reached_notified = True
            
            # Create popup window
            popup = tk.Toplevel(self.root)
            popup.title("Target Reached!")
            popup.geometry("400x200")
            popup.resizable(False, False)
            
            # Center the popup
            popup.transient(self.root)
            popup.grab_set()
            
            # Configure popup
            popup.configure(bg='#e8f5e8')
            
            # Add content
            title_label = tk.Label(popup, text="🎉 Congratulations!", 
                                 font=("Arial", 16, "bold"), 
                                 bg='#e8f5e8', fg='#2e7d32')
            title_label.pack(pady=20)
            
            if remaining_minutes == 0:
                message = "You've reached your target hours!"
            else:
                over_hours, over_mins = divmod(abs(remaining_minutes), 60)
                message = f"You've exceeded your target by {over_hours} hours and {over_mins} minutes!"
            
            message_label = tk.Label(popup, text=message, 
                                   font=("Arial", 12), 
                                   bg='#e8f5e8', fg='#1b5e20')
            message_label.pack(pady=10)
            
            # Add close button
            close_button = ttk.Button(popup, text="Awesome!", 
                                    command=popup.destroy)
            close_button.pack(pady=20)
            
            # Play system sound (if available)
            try:
                popup.bell()
            except:
                pass
            
            # Auto-close after 10 seconds
            popup.after(10000, popup.destroy)
    
    def save_temp_data(self):
        """Save current data to temporary file"""
        try:
            data = {
                'input_text': self.input_text.get("1.0", tk.END).strip(),
                'target_hours': self.target_var.get(),
                'auto_update_enabled': self.auto_update_enabled.get(),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.temp_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            pass
    
    def load_temp_data(self):
        """Load data from temporary file if it exists"""
        try:
            if os.path.exists(self.temp_file):
                with open(self.temp_file, 'r') as f:
                    data = json.load(f)
                
                # Load the saved data
                if data.get('input_text'):
                    self.input_text.insert("1.0", data['input_text'])
                
                if data.get('target_hours'):
                    self.target_var.set(data['target_hours'])
                
                if 'auto_update_enabled' in data:
                    self.auto_update_enabled.set(data['auto_update_enabled'])
        except Exception as e:
            pass
    
    def auto_save(self, *args):
        """Auto-save data when user types or changes settings"""
        self.save_temp_data()
    
    def on_closing(self):
        """Handle window closing - save data before exit"""
        self.running = False
        self.save_temp_data()
        self.root.destroy()
    
    def calculate(self, silent=False):
        """Calculate the total time from the input text area"""
        input_text = self.input_text.get("1.0", tk.END)
        time_list = [line.strip() for line in input_text.split("\n")]
        
        try:
            target_hours = float(self.target_var.get())
        except ValueError:
            if not silent:
                messagebox.showerror("Error", "Please enter a valid number for target hours")
            return
        
        try:
            total_result, remaining_result, total_minutes, remaining_minutes = calculate_time_sum(time_list, target_hours)
            self.result_var.set(total_result)
            self.remaining_var.set(remaining_result)
            
            # Update last updated timestamp
            now = datetime.now().strftime("%H:%M:%S")
            self.last_updated_var.set(f"Last updated: {now}")
            
            # Update result display color based on target status
            if remaining_minutes <= 0:
                self.remaining_display.config(style="Success.TLabel")
            elif remaining_minutes > 0:
                self.remaining_display.config(style="Warning.TLabel")
            
            # Check for target reached notification
            if self.last_remaining_minutes is not None:
                # Target just reached
                if self.last_remaining_minutes > 0 and remaining_minutes <= 0:
                    self.show_target_reached_popup(remaining_minutes)
            
            self.last_remaining_minutes = remaining_minutes
            
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def clear(self):
        """Clear the input text area"""
        self.input_text.delete("1.0", tk.END)
        self.result_var.set("0 hours and 0 minutes")
        self.remaining_var.set("")
        self.last_updated_var.set("")
        self.target_reached_notified = False
        self.last_remaining_minutes = None
    
    def load_example(self):
        """Load example data into text area"""
        self.clear()
        example_data = """5:00 – 8:05am
10:15 – 11:00am
-7:00 – 8:06am
8:20 – 9:40am
7:00am – 2:30pm
9:45 –"""
        self.input_text.insert("1.0", example_data)

def main():
    root = tk.Tk()
    app = TimeCalculatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()