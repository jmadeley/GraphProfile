import tkinter as tk
from collections import namedtuple
from tkinter import filedialog
import xml.etree.ElementTree as ET
from unittest import case

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import CoolingModel


def browse_file():
    global xml_tree, fig, ax  # Declare globals to access them later
    filename = filedialog.askopenfilename(
        title="Select Profile XML File",
        filetypes=(("XML files", "*.profile"), ("All files", "*.*"))
    )

    if filename:
        try:
            xml_tree = ET.parse(filename)  # Parse the XML file
            # Now that the XML is parsed, enable the graph button.
            graph_profile()
        except ET.ParseError as e:
            status_label.config(text=f"Error parsing XML: {e}")
        except Exception as e:
            status_label.config(text=f"An error occurred: {e}")
    else:
        status_label.config(text="No file selected")


def graph_profile():
    global xml_tree, fig, ax  # Access the globals

    if xml_tree is not None:
        try:
            # Clear previous plot if any
            ax.clear()  # Clear the axes
            fig.canvas.draw()  # Important! Redraw the canvas.

            GraphProfile(xml_tree, ax)  # Call the graphing function
            fig.canvas.draw()  # Update the Matplotlib canvas


        except Exception as e:
            status_label.config(text=f"Error graphing: {e}")

    else:
        status_label.config(text="No XML file loaded.")


def GraphProfile(xml_tree, ax):  # Placeholder function. Implement later!
    """
    This function will take the XML tree object and the matplotlib axes object
    as input and plot the profile data.  This is a placeholder.
    """
    # Example placeholder plot (replace with your actual plotting logic)
    try:
        axPressure = ax.twinx()
        root = xml_tree.getroot()
        profileName = getKey(root, 'Name')
        profileFormatVersion = getKey(root, 'FormatVersion')
        temperature_segments = get_temperature_segments(root)
        heating_segments = get_pressure_segments(root, "HeatingSwitchPoints/VacuumSwitchPoint")
        cooling_segments = get_pressure_segments(root, "CoolingSwitchPoints/VacuumSwitchPoint")
        modifiers = get_modifiers(root,"Modifiers")
        x, y = get_heating_segments(temperature_segments)
        cooling_times, cooling_temperatures = CoolingModel.get_cooling_curves(y[-1], modifiers.EndTemperature, x[-1], modifiers.MaximumActiveCoolingTemperature)
        times = x + cooling_times
        temperatures = y + cooling_temperatures
        ax.plot(times, temperatures)
        ax.set_title(profileName)
        ax.set_xlabel("Time (hours)")
        ax.set_ylabel("Temperature (Celsius)")
        ax.set_ylim(0, 1600)
        ax.grid(True)

        axPressure.set_ylabel("Pressure (Torr)")
        axPressure.set_ylim(0, 800)


    except Exception as e:
        status_label.config(text=f"An error occurred: {e}")


def getKey(root, name):
    tag = root.find(name)
    if tag is not None:
        tagText = tag.text
        return tagText
    else:
        return None


def get_temperature_segments(root):
    try:
        segments = []

        segments_elements = root.findall('Segments/Segment')  # Find all Segment elements

        for segment_element in segments_elements:
            segment_data = {}
            segment = namedtuple("Segment", ["hold", "slew", "target"])
            hold = 0
            slew = 0
            target = 0
            for child in segment_element:  # Iterate through segment's children
                match child.tag:
                    case "HoldTimeHours":
                        hold = float(child.text)
                    case "SlewRateCPerMin":
                        slew = float(child.text)
                    case "TargetTemperature":
                        target = float(child.text)
            segments.append(segment(hold, slew, target))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    return segments


def get_pressure_segments(root, name):
    try:
        segments = []

        segments_elements = root.findall(name)  # Find all Segment elements

        for segment_element in segments_elements:
            segment = namedtuple("Segment", ["TemperatureCelsius", "Gas", "PressureTorr", "FrontHeat"])
            TemperatureCelsius = 0
            Gas = "Vacuum"
            PressureTorr = 0
            FrontHeat = False
            for child in segment_element:  # Iterate through segment's children
                match child.tag:
                    case "Gas":
                        Gas = child.text
                    case "PressureTorr":
                        PressureTorr = float(child.text)
                    case "TemperatureCelsius":
                        TemperatureCelsius = float(child.text)
                    case "FrontHeat":
                        FrontHeat = bool(child.text)
            segments.append(segment(TemperatureCelsius, Gas, PressureTorr, FrontHeat))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    return segments

def get_modifiers(root, name):
    EndTemperature = 150
    MaximumActiveCoolingTemperature = 1050
    try:
        modifiers = root.findall(name)
        for modifier in modifiers:
            for child in modifier:
                match child.tag:
                    case "EndTemperature":
                        EndTemperature = float(child.text)
                    case "MaximumActiveCoolingTemperature":
                        x = float(child.text)
                        if x > 50:
                            MaximumActiveCoolingTemperature = x
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    modifierTuple = namedtuple("Modifier", ["EndTemperature", "MaximumActiveCoolingTemperature"])
    return modifierTuple(EndTemperature, MaximumActiveCoolingTemperature)


def get_heating_segments(segments):
    temperature = 20
    time = 0
    x = [time]
    y = [temperature]
    for segment in segments:
        if abs(segment.slew) > 0.01:
            time += abs((segment.target - temperature) / segment.slew / 60)
            temperature = segment.target
            x.append(time)
            y.append(temperature)
        if segment.hold > 0:
            time += segment.hold
            x.append(time)
            y.append(temperature)
    return x,y




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
fig, ax = plt.subplots()  # Create figure and axes
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)  # Make canvas resizeable
# canvas.get_tk_widget().pack(pady=10)  # Pack the canvas into the GUI

# Graph button (initially disabled)
# graph_button = tk.Button(root, text="Graph Profile", command=graph_profile, state=tk.DISABLED)
# graph_button.pack()

xml_tree = None  # Initialize xml_tree to None
root.mainloop()
