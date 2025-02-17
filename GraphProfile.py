import tkinter as tk
from collections import namedtuple
from tkinter import filedialog
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import CoolingModel


def browse_file():
    """Open a file dialog to select an XML profile file and parse it."""
    global xml_tree
    filename = filedialog.askopenfilename(
        title="Select Profile XML File",
        filetypes=(("XML files", "*.profile"), ("All files", "*.*"))
    )

    if filename:
        try:
            xml_tree = ET.parse(filename)
            graph_profile()
            status_label.config(text="Profile loaded successfully.")
        except ET.ParseError as e:
            status_label.config(text=f"Error parsing XML: {e}")
        except Exception as e:
            status_label.config(text=f"An error occurred: {e}")
    else:
        status_label.config(text="No file selected")


def graph_profile():
    """Graph the profile data from the parsed XML."""
    global xml_tree

    if xml_tree is not None:
        try:
            fig.canvas.draw()
            profile_name = get_xml_value(xml_tree, 'Name')
            fig.suptitle(profile_name)
            plot_profile(xml_tree, ax)
            fig.canvas.draw()
        except Exception as e:
            status_label.config(text=f"Error graphing: {e}")
            raise
    else:
        status_label.config(text="No XML file loaded.")


def plot_profile(xml_tree, ax):
    """Plot the temperature and pressure profiles."""
    try:
        root = xml_tree.getroot()
        temperature_segments = extract_temperature_segments(root)
        heating_pressure_segments = extract_pressure_segments(root, "HeatingSwitchPoints/VacuumSwitchPoint")
        cooling_pressure_segments = extract_pressure_segments(root, "CoolingSwitchPoints/VacuumSwitchPoint")
        modifiers = extract_modifiers(root, "Modifiers")
        times, temperatures = calculate_heating_segments(temperature_segments)
        cooling_times, cooling_temperatures = CoolingModel.get_cooling_curves(
            temperatures[-1], modifiers.end_temperature, times[-1], modifiers.max_active_cooling_temp
        )
        times.extend(cooling_times)
        temperatures.extend(cooling_temperatures)

        ax[0].clear()
        ax[0].set_xlim(auto=True)  # Reset x-axis limits
        plt.setp(ax[0].get_xticklabels(), visible=True)
        ax[0].plot(times, temperatures)
        ax[0].set_title("Temperatures")
        ax[0].set_xlabel("Time (hours)")
        ax[0].set_ylabel("Temperature (Celsius)")
        ax[0].set_ylim(0, 1600)
        ax[0].set_xlim(xmin=0)
        ax[0].grid(True)

        ax[1].clear()
        ax[1].set_xlim(auto=True)  # Reset x-axis limits
        ax[1].set_title("Pressures")
        ax[1].set_xlabel("Time (hours)")
        ax[1].set_ylabel("Pressure (Torr)")
        ax[1].set_xlim(xmin=0)

        ax[1].grid(True)

        pressure_times, pressures = calculate_pressure_graph(
            heating_pressure_segments, cooling_pressure_segments, times, temperatures
        )
        ax[1].plot(pressure_times, pressures)
        # Synchronize x-axis limits and ticks
        ax[1].set_xlim(ax[0].get_xlim())  # Set the same x-axis limits
        ax[1].set_xticks(ax[0].get_xticks())  # Set the same x-axis ticks

        plt.tight_layout()
        ax[1].relim()  # Recalculate limits
        ax[1].autoscale_view()  # Adjust the view
        fig.canvas.draw()
    except Exception as e:
        ax[0].clear()
        ax[1].clear()
        raise


def get_xml_value(root, tag_name):
    """Retrieve the text value of a specified XML tag."""
    tag = root.find(tag_name)
    return tag.text if tag is not None else None


def extract_temperature_segments(root):
    """Extract temperature segments from the XML."""
    segments = []
    segment_elements = root.findall('Segments/Segment')

    for segment_element in segment_elements:
        segment = namedtuple("Segment", ["hold", "slew", "target"])
        hold, slew, target = 0, 0, 0
        for child in segment_element:
            match child.tag:
                case "HoldTimeHours":
                    hold = float(child.text)
                case "SlewRateCPerMin":
                    slew = float(child.text)
                case "TargetTemperature":
                    target = float(child.text)
        segments.append(segment(hold, slew, target))
    return segments


def extract_pressure_segments(root, path):
    """Extract pressure segments from the XML."""
    segments = []
    segment_elements = root.findall(path)

    for segment_element in segment_elements:
        segment = namedtuple("Segment", ["temperature", "gas", "pressure", "front_heat"])
        temperature, gas, pressure, front_heat = 0, "Vacuum", 0, False
        for child in segment_element:
            match child.tag:
                case "Gas":
                    gas = child.text
                case "PressureTorr":
                    pressure = float(child.text)
                case "TemperatureCelsius":
                    temperature = float(child.text)
                case "FrontHeat":
                    front_heat = bool(child.text)
        segments.append(segment(temperature, gas, pressure, front_heat))
    return segments


def extract_modifiers(root, path):
    """Extract modifiers from the XML."""
    end_temperature = 150
    max_active_cooling_temp = 1050
    modifiers = root.findall(path)

    for modifier in modifiers:
        for child in modifier:
            match child.tag:
                case "EndTemperature":
                    end_temperature = float(child.text)
                case "MaximumActiveCoolingTemperature":
                    temp = float(child.text)
                    if temp > 50:
                        max_active_cooling_temp = temp
    Modifier = namedtuple("Modifier", ["end_temperature", "max_active_cooling_temp"])
    return Modifier(end_temperature, max_active_cooling_temp)


def calculate_heating_segments(segments):
    """Calculate heating segments based on temperature changes."""
    temperature, time = 20, 0
    times, temperatures = [time], [temperature]

    for segment in segments:
        if abs(segment.slew) > 0.01:
            time += abs((segment.target - temperature) / segment.slew / 60)
            temperature = segment.target
            times.append(time)
            temperatures.append(temperature)
        if segment.hold > 0:
            time += segment.hold
            times.append(time)
            temperatures.append(temperature)
    return times, temperatures


def calculate_pressure_graph(heating_segments, cooling_segments, times, temperatures):
    """Calculate the pressure graph based on heating and cooling segments."""
    pressure_times, pressures = [], []
    heating_interpolator = CoolingModel.get_reverse_interpolator(times, temperatures, True)
    cooling_interpolator = CoolingModel.get_reverse_interpolator(times, temperatures, False)
    max_temperature = max(temperatures)
    last_pressure, last_time = 0.0, 0.25

class PressureGraph:
    """Class to encapsulate pressure-related data."""

    def __init__(self):
        self.pressures = []
        self.pressure_times = []
        self.last_pressure = 0.0
        self.last_time = 0.0

    def add_pressure_plateau(self, pressure, time):
        """Add a pressure plateau to the pressures and pressure_times lists."""
        SLEW = 300
        pressure = float(pressure)
        if pressure > 20:
            time_to_repressurize = abs( (pressure-self.last_pressure) / SLEW)
        else:
            time_to_repressurize = 0
        if self.last_time > time:
            raise Exception("Insufficient time to adjust pressure between pressure changes.")
        time = float(max(time,self.last_time))
        self.pressures.extend([self.last_pressure, self.last_pressure])
        self.pressure_times.extend([self.last_time, time])
        self.last_pressure = float(pressure)
        self.last_time = time + time_to_repressurize

    def get_last_time(self):
        """Return the last time."""
        return float(self.last_time)

def calculate_pressure_graph(heating_segments, cooling_segments, times, temperatures):
    """Calculate the pressure graph based on heating and cooling segments."""
    graph = PressureGraph()
    heating_interpolator = CoolingModel.get_reverse_interpolator(times, temperatures, True)
    cooling_interpolator = CoolingModel.get_reverse_interpolator(times, temperatures, False)
    max_temperature = max(temperatures)

    graph.add_pressure_plateau(0, 0)
    graph.add_pressure_plateau(0, 0.25)

    for segment in heating_segments:
        if segment.temperature > max_temperature:
            graph.add_pressure_plateau(segment.pressure, heating_interpolator.y[-1])
            break
        time = heating_interpolator(segment.temperature)
        if time < 0.25:
            continue
        pressure = segment.pressure
        graph.add_pressure_plateau(pressure, time)
    graph.add_pressure_plateau(graph.last_pressure, heating_interpolator.y[-1])
    for segment in cooling_segments:
        if segment.temperature > max_temperature:
            temperature = max_temperature
        else:
            temperature = segment.temperature
        time = cooling_interpolator(temperature)
        if time < graph.last_time:
            graph.last_pressure = segment.pressure
            continue
        graph.add_pressure_plateau(segment.pressure, time)
    graph.add_pressure_plateau(graph.last_pressure, cooling_interpolator.y[0])
    return graph.pressure_times, graph.pressures



# Main GUI setup
root = tk.Tk()
root.title("Profile Viewer V1.0")

# File browsing button
browse_button = tk.Button(root, text="Browse for Profile", command=browse_file)
browse_button.pack(pady=10)

# Status label
status_label = tk.Label(root, text=" ")
status_label.pack()

# Matplotlib figure and canvas
fig, ax = plt.subplots(2, 1, sharex=True)
plt.tight_layout()
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

xml_tree = None
root.mainloop()
