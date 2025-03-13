import math
import os
import tkinter as tk
from collections import namedtuple
from tkinter import filedialog
import tkinter.messagebox as messagebox

from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import CoolingModel


def browse_file():
    """Open a file dialog to select an XML profile file and parse it."""
    #global xml_tree
    filename = filedialog.askopenfilename(
        title="Select Profile XML File",
        filetypes=(("XML files", "*.profile"), ("All files", "*.*"))
    )

    if filename:
        basename = os.path.basename(filename)
        try:
            xml_tree = ET.parse(filename)
            graph_profile(xml_tree)
            status_label.config(text=f"Profile '{basename}'\n loaded successfully.")
        except ET.ParseError as e:
            status_label.config(text=f"Error parsing XML in '{basename}':\n {e}")
            messagebox.showerror("XML Parse Error", f"Error parsing XML in '{basename}':\n {e}")
        except Exception as e:
            status_label.config(text=f"An error occurred in '{basename}':\n {e}")
            messagebox.showerror("Error", f"An error occurred in '{basename}':\n {e}")
    else:
        status_label.config(text="No file selected")


def graph_profile(xml_tree):
    """Graph the profile data from the parsed XML."""

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


import xml.etree.ElementTree as ET
from matplotlib.axes import Axes
from typing import List

def plot_profile(xml_tree: ET.ElementTree, ax: List[Axes]) -> None:
    """
    Plot the temperature and pressure profiles extracted from an XML tree.

    :param xml_tree: Parsed XML tree containing profile data.
    :param ax: List of Matplotlib Axes to plot the temperature and pressure.
    """
    try:
        root = xml_tree.getroot()
        temperature_segments = extract_temperature_segments(root)
        validate_segments(temperature_segments, "HeatingSwitchPoints")

        heating_pressure_segments = extract_pressure_segments(root, "HeatingSwitchPoints/VacuumSwitchPoint")
        cooling_pressure_segments = extract_pressure_segments(root, "CoolingSwitchPoints/VacuumSwitchPoint")
        validate_segments(cooling_pressure_segments, "CoolingSwitchPoints")

        modifiers = extract_modifiers(root, "Modifiers")
        times, temperatures = calculate_heating_segments(temperature_segments)

        cooling_times, cooling_temperatures = CoolingModel.get_cooling_curves(
            temperatures[-1], modifiers.end_temperature, times[-1], modifiers.max_active_cooling_temp
        )
        times.extend(cooling_times)
        temperatures.extend(cooling_temperatures)

        # Calculate total time
        total_time = calculate_total_time(times)

        plot_temperature_profile(ax[0], times, temperatures, total_time)
        plot_pressure_profile(ax[1], heating_pressure_segments, cooling_pressure_segments, times, temperatures)

        fig.canvas.draw()

    except Exception as e:
        handle_plotting_exception(ax, e)

def validate_segments(segments: List, tag: str) -> None:
    """Validate the presence of segments."""
    if not segments:
        raise ValueError(f"No {tag} found.")

def calculate_total_time(times: List) -> float:
    """Calculate the total time of the profile."""
    return times[-1] if times else 0

def plot_temperature_profile(ax: Axes, times: List, temperatures: List, total_time: float) -> None:
    """Plot the temperature profile on the provided Axes."""
    ax.clear()
    ax.set_xlim(auto=True)
    ax.plot(times, temperatures, label='Temperature (°C)')
    ax.set_title("Temperatures")
    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Temperature (Celsius)")
    ax.set_ylim(0, 1500)
    ax.set_xlim(xmin=0)
    configure_temperature_axis(ax)
    ax.text(0.5, 0.05, f'Estimated Time: {total_time:.1f} hours', transform=ax.transAxes,
            fontsize=10, verticalalignment='bottom', horizontalalignment='center', backgroundcolor='white')

def configure_temperature_axis(ax: Axes) -> None:
    """Configure the appearance and grid settings of the temperature axis."""
    ax.yaxis.set_major_locator(ticker.MultipleLocator(500))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(100))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.grid(which='major', linestyle='-', linewidth=1.5)
    ax.grid(which='minor', linestyle='-', linewidth=0.5)
    plt.setp(ax.get_xticklabels(), visible=True)

def plot_pressure_profile(ax: Axes, heating_segments, cooling_segments, times, temperatures) -> None:
    """Plot the pressure profile on the provided Axes."""
    ax.clear()
    ax.set_title("Pressures")
    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Pressure (Torr)")
    configure_pressure_axis(ax)

    pressure_times, pressures = calculate_pressure_graph(
        heating_segments, cooling_segments, times, temperatures
    )
    ax.plot(pressure_times, pressures)
    synchronize_x_axis(ax, pressures, pressure_times)

def configure_pressure_axis(ax: Axes) -> None:
    """Configure the appearance and grid settings of the pressure axis."""
    ax.yaxis.set_major_locator(ticker.MultipleLocator(50))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(10))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.grid(which='major', linestyle='-', linewidth=1.5)
    ax.grid(which='minor', linestyle='-', linewidth=0.5)
    plt.setp(ax.get_yticklabels(), visible=True)

def synchronize_x_axis(ax: Axes, pressures: List, pressure_times: List) -> None:
    """Synchronize x-axis limits and ticks between temperature and pressure plots."""
    ax.set_xlim(ax.get_xlim())  # Set the same x-axis limits
    ax.set_xticks(ax.get_xticks())  # Set the same x-axis ticks
    ax.set_xlim(0, max(pressure_times))
    upper_y_limit = round_up_to_nearest_n(max(pressures)+10, 50)
    ax.set_ylim(0, upper_y_limit)
    plt.tight_layout()
    ax.relim()  # Recalculate limits
    ax.autoscale_view()

def handle_plotting_exception(ax: List[Axes], e: Exception) -> None:
    """Handle exceptions during plotting by clearing the axes and raising the error."""
    ax[0].clear()
    ax[1].clear()
    raise e

def round_up_to_nearest_n(number, n):
    """Round up the given number to the nearest n."""
    return math.ceil(number / n) * n

def get_xml_value(root: ET.Element, tag_name: str) -> Optional[str]:
    """
    Retrieve the text value of a specified XML tag.

    :param root: The root element of the XML tree.
    :param tag_name: The name of the tag to search for.
    :return: The text value of the tag, or None if the tag is not found.
    """
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

class PressureGraph:
    """Class to encapsulate pressure-related data."""

    def __init__(self):
        self.pressures = []
        self.pressure_times = []
        self.last_pressure = 0.0
        self.last_time = 0.0

    def add_pressure_plateau(self, pressure, time, end_of_heating=False):
        """Add a pressure plateau to the pressures and pressure_times lists."""
        slew = 300
        pressure = float(pressure)
        if end_of_heating:
            time_to_pressurize = 0
        elif pressure > 20:
            time_to_pressurize = abs( (pressure-self.last_pressure) / slew)
        else:
            time_to_pressurize = 0
        if self.last_time > time:
            raise Exception("Insufficient time to adjust pressure between pressure changes.")
        time = float(max(time,self.last_time))
        if time-self.last_time > 0.001:
            self.pressures.extend([self.last_pressure, self.last_pressure])
            self.pressure_times.extend([self.last_time, time])
        self.last_pressure = float(pressure)
        self.last_time = time + time_to_pressurize

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
            graph.add_pressure_plateau(segment.pressure, heating_interpolator.y[-1], True)
            break
        time = heating_interpolator(segment.temperature)
        if time < 0.25:
            graph.add_pressure_plateau(segment.pressure, 0.25)
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
root.title("Profile Viewer V0.91")

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
