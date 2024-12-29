"""
 * @file main.py
 * @brief Python script for sending and receiving PWM and Lux data via a serial interface with a GUI.
 *
 * This script provides a graphical interface to send PWM and desired Lux values to a microcontroller.
 * It listens for incoming feedback and data from the microcontroller and plots Lux data in real-time.
 *
 * @details The application uses Tkinter for the GUI, Matplotlib for plotting, and pySerial for serial communication.
 * Communication involves sending JSON-encoded messages and interpreting JSON responses.
 */
"""
import tkinter as tk
import serial
import json
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Lock to ensure thread-safe access to the serial port.
serial_lock = threading.Lock()
# Bounds for the desired Lux values.
low_lux, high_lux = 0, 1000
# Lists for storing Lux values and corresponding timestamps.
lux_values = []
timestamps = []
# Flags for managing the Lux data listening process.
lux_listening = False
lux_thread = None


"""
 * @brief Send PWM and Lux values to the microcontroller.
 *
 * @param ser Serial connection object.
 *
"""


def send_data(ser):
    try:
        pwm_value = int(pwm_entry.get())
        lux_value = int(lux_entry.get())
        priority = 1 if priority_var.get() == "PWM" else 0

        if not (low_lux <= lux_value <= high_lux):
            status_label.config(text=f"Lux value is out of possible range({low_lux};{high_lux})!", fg="red")

        elif not (0 <= pwm_value <= 999):
            status_label.config(text=f"PWM value is out of possible range(0;999)!", fg="red")
        else:
            data = {
                "LED": lux_value,
                "PWM": pwm_value,
                "PRIORITY": priority
            }
            json_data = json.dumps(data)
            with serial_lock:
                ser.write(json_data.encode('utf-8'))
            status_label.config(text="Data sent successfully!", fg="green")
            ser.flush()

    except ValueError:
        status_label.config(text="Please enter valid integers!", fg="red")
    except Exception as e:
        status_label.config(text=f"Error: {str(e)}", fg="red")


"""
 * @brief Listen to USART communication for feedback and configuration updates.
 *
 * @param ser Serial connection object.
 *
"""


def listen_to_usart(ser):
    global low_lux
    global high_lux
    buffer = ""
    while True:
        try:
            if ser.in_waiting > 0:
                with serial_lock:
                    incoming_data = ser.readline().decode('utf-8').strip()
                    buffer += incoming_data

                while True:
                    if buffer:
                        end_pos = buffer.find('}')
                        if end_pos != -1:
                            json_data = buffer[:end_pos + 1]
                            data = json.loads(json_data)

                            if 'success' in data and 'message' in data:
                                success = data.get("success", "No success value")
                                message = data.get("message", "No message")
                                feedback_label.config(text=f"Feedback - Success: {success}, Message: {message}")
                            elif 'operation' in data and 'message' in data and 'low_lux' in data and 'high_lux' in data:
                                # success = data.get("success", "No success value")
                                # message = data.get("message", "No message")
                                low_lux = data.get("low_lux", "No low_lux value")
                                high_lux = data.get("high_lux", "No high_lux value")
                            buffer = buffer[end_pos + 1:]
                        else:
                            break
                    else:
                        break

            time.sleep(0.1)

        except Exception as e:
            print(f"Error while listening to USART: {e}")
            time.sleep(0.1)


"""
 * @brief Continuously listen for real-time Lux data and update the GUI.
 *
 * @param ser Serial connection object.
 *
"""


def listen_for_lux(ser):
    global lux_listening
    while lux_listening:
        try:
            if ser.in_waiting > 0:
                with serial_lock:
                    incoming_data = ser.readline().decode('utf-8').strip()
                if incoming_data:
                    try:
                        data = json.loads(incoming_data)
                        if data.get("operation") == "data" and "data" in data:
                            lux_value = data["data"]
                            lux_value_label.config(text=f"Current Lux: {lux_value}")
                            timestamps.append(time.time())
                            lux_values.append(lux_value)
                            if len(timestamps) > 100:
                                timestamps.pop(0)
                                lux_values.pop(0)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON received: {incoming_data}")

            time.sleep(0.1)
        except Exception as e:
            print(f"Error while listening for lux data: {e}")
            time.sleep(0.1)


"""
 * @brief Start or stop listening for Lux data.
 *
"""


def start_stop_lux_listening():
    global lux_listening, lux_thread, timestamps, lux_values

    if lux_listening:
        lux_listening = False
        lux_status_label.config(text="Stopped listening for Lux data.")
    else:
        timestamps.clear()
        lux_values.clear()
        ax.clear()
        canvas.draw()

        lux_listening = True
        lux_thread = threading.Thread(target=listen_for_lux, args=(serial_conn,), daemon=True)
        lux_thread.start()
        lux_status_label.config(text="Listening for Lux data...")


"""
 * @brief Update the Lux plot in real-time.
 *
"""


def update_plot():
    while True:
        if len(timestamps) > 0:
            ax.clear()
            ax.plot(timestamps, lux_values, label="Lux", color="blue")
            ax.set_title("Lux Values Over Time")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Lux")
            ax.legend()
            canvas.draw()
        time.sleep(1)


"""
 * @brief Start the thread responsible for updating the Lux plot.
 *
"""


def start_plot_thread():
    plot_thread = threading.Thread(target=update_plot, daemon=True)
    plot_thread.start()


# Main script entry point. Initialize GUI and serial communication.

# Create the main application window.
root = tk.Tk()
root.title("PWM and Lux Value Sender")
root.geometry("800x1000")

# Create and configure PWM width input field.
pwm_label = tk.Label(root, text="Enter PWM width:", font=("Arial", 14))
pwm_label.pack(pady=20)
pwm_entry = tk.Entry(root, font=("Arial", 14))
pwm_entry.insert(0, "100")
pwm_entry.pack(pady=10)

# Create and configure desired Lux value input field.
lux_label = tk.Label(root, text="Enter desired Lux value:", font=("Arial", 14))
lux_label.pack(pady=20)
lux_entry = tk.Entry(root, font=("Arial", 14))
lux_entry.insert(0, "50")
lux_entry.pack(pady=10)

# Create and configure the dropdown menu for priority selection.
priority_label = tk.Label(root, text="Select what to prioritize:", font=("Arial", 14))
priority_label.pack(pady=20)
priority_var = tk.StringVar(value="PWM")
priority_dropdown = tk.OptionMenu(root, priority_var, "PWM", "LUX")
priority_dropdown.config(font=("Arial", 14))
priority_dropdown.pack(pady=10)

# Create and configure the "Send Data" button.
send_button = tk.Button(
    root, text="Send Data", font=("Arial", 14),
    command=lambda: send_data(serial_conn)
)
send_button.pack(pady=20)

# Create and configure labels for status and feedback messages.
status_label = tk.Label(root, text="", font=("Arial", 14))
status_label.pack(pady=10)
feedback_label = tk.Label(root, text="Waiting for feedback...", font=("Arial", 14))
feedback_label.pack(pady=20)

# Create and configure labels for real-time Lux value display.
lux_value_label = tk.Label(root, text="Current Lux: N/A", font=("Arial", 14))
lux_value_label.pack(pady=20)
lux_status_label = tk.Label(root, text="", font=("Arial", 14))
lux_status_label.pack(pady=10)

# Create and configure the "Start/Stop Listening for Lux Data" button.
lux_button = tk.Button(
    root, text="Start/Stop Listening for Lux Data", font=("Arial", 14),
    command=start_stop_lux_listening
)
lux_button.pack(pady=20)

# Create a Matplotlib figure and embed it into the GUI using FigureCanvasTkAgg.
fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

# Start the thread responsible for updating the Lux plot in real-time.
start_plot_thread()

# Initialize the serial connection.
serial_conn = serial.Serial('COM5', 9600, timeout=1)

# Check if the serial connection is open.
if serial_conn.is_open:
    print("Serial connection established.")
else:
    print("Error: Serial connection not open.")

# Start a separate thread to listen for USART feedback.
listen_thread = threading.Thread(
    target=listen_to_usart, args=(serial_conn,), daemon=True
)
listen_thread.start()

# Run the main GUI event loop.
root.mainloop()
