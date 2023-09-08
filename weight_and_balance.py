import json
import os
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# Conversion constants
IN2CM = 2.54
CM2MM = 10
KG100LL = 0.71

# Station names
class STATIONS:
    FRONT_SEATS = "front_seats"
    BACK_SEATS = "back_seats"
    FRONT_BAGGAGE = "front_baggage"
    BACK_BAGGAGE = "back_baggage"
    FUEL = "fuel"


# Available planes
class CALLSIGNS:
    DEXAV = "D-EXAV"
    DEXBS = "D-EXBS"


class C172S_WB:
    """Weight and balance calculator for the Cessna 172S."""

    def __init__(self, callsign: str):
        if callsign == CALLSIGNS.DEXBS:
            self.empty_mass_kg = 773.16
            self.empty_arm_cm = 101.62
            self.empty_moment = round(
                self.empty_mass_kg * self.empty_arm_cm, 2  # 78572.54 in the book
            )
            self.date = datetime(2017, 5, 18)
        elif callsign == CALLSIGNS.DEXAV:
            self.empty_mass_kg = 749
            self.empty_arm_cm = 106.805
            self.empty_moment = round(
                self.empty_mass_kg * self.empty_arm_cm, 2  # 79997.00 in the book
            )
            self.date = datetime(2022, 5, 10)
        else:
            raise ValueError("Double check callsign")

        self.callsign = callsign
        # From Cessna 172S POH
        self.arms = {
            STATIONS.FRONT_SEATS: 37 * IN2CM,
            STATIONS.BACK_SEATS: 73 * IN2CM,
            STATIONS.FRONT_BAGGAGE: 95 * IN2CM,
            STATIONS.BACK_BAGGAGE: 123 * IN2CM,
            STATIONS.FUEL: 48 * IN2CM,
        }

        self.loading = defaultdict(dict)

    def load(self, weight_kg: float, station: str, name: str) -> None:
        """Put a load into the plane at the specified station."""
        self.loading[station][name.capitalize()] = weight_kg

    def fuel(self, liters: float) -> None:
        """Add fuel to the plane."""
        self.loading[STATIONS.FUEL]["Fuel"] = liters * KG100LL

    def total_weight(self, with_fuel: bool = True) -> float:
        """Total weight."""
        total_weight = self.empty_mass_kg
        for station, weights in self.loading.items():
            if station == STATIONS.FUEL and not with_fuel:
                continue
            total_weight += np.sum(np.array(list(weights.values())))
        return round(total_weight, 2)

    def total_moment(self, with_fuel: bool = True) -> float:
        """Total moment"""
        total_moment = self.empty_moment
        for station, arm in self.arms.items():
            if station == STATIONS.FUEL and not with_fuel:
                continue
            weight = self.loading.get(station, {})
            total_moment += np.sum(np.array(list(weight.values())) * arm)
        return round(total_moment, 2)

    def CoG(self, with_fuel: bool = True) -> float:
        """Center of gravity."""
        return round(self.total_moment(with_fuel) / self.total_weight(with_fuel), 2)


def _underline(pdf, x: float, y: float, text: str, font, fontsize) -> None:
    """Underline the given text and write."""
    linelength = stringWidth(text, font, fontsize)
    pdf.drawString(x, y, text)
    pdf.line(x, y - 2, x + linelength, y - 2)


def _sanitize_station(station: str) -> str:
    """Make station humanreadable."""
    return station.replace("_", " ").capitalize()


def _map2range(
    graph_val: float, max_graph: float, min_graph: float, max_px: float, min_px: float
) -> float:
    """Map from one range to another."""
    graph_range = max_graph - min_graph
    px_range = max_px - min_px
    return (((graph_val - min_graph) * px_range) / graph_range) + min_px


def create_pdf(plane: C172S_WB):
    """Create weight and balance pdf."""

    # Base constants to control how the pdf looks and behaves
    font = "Courier"
    fontsize = 12
    width, height = A4
    newline = 15
    header_new_line = 20
    start_height = 780

    filedate = datetime.today().strftime("%y%m%d")
    pdf = canvas.Canvas(
        f"{filedate}_{plane.callsign}_weight_and_balance.pdf", pagesize=A4
    )
    pdf.setLineWidth(0.3)
    pdf.setFont("Helvetica", fontsize)

    # Draw the header
    date = datetime.today().strftime("%d/%m/%y")
    pdf.drawString(30, start_height, "Weight and Balance", mode=1)
    pdf.drawString(30, start_height - header_new_line, "Cessna 172S")
    date_width = stringWidth(date, font, fontsize)
    pdf.drawString(500, start_height, date)
    pdf.line(  # line across the entire page
        30,
        start_height - header_new_line - 5,
        500 + date_width,
        start_height - header_new_line - 5,
    )
    pdf.setFont(font, fontsize)  # cooler font for "calculations"

    # Airplane specific data at the top
    start = start_height - header_new_line - 5 - header_new_line
    pdf.drawString(30, start, f"Aircraft: {plane.callsign}")
    start -= header_new_line
    pdf.drawString(30, start, f"Weighing Date: {plane.date.strftime('%d/%m/%y')}")

    # Create some offsets so text is aligned
    weight_x = 170  # weight x offset
    arm_x = 310  # arm x offset
    moment_x = 420  # moment x offset
    weight_right_offset = stringWidth("Empty Weight", font, fontsize)
    # A bigger placeholder arm which should be long enough to encompass other arms,
    # so that they are all aligned
    arm_right_offset = stringWidth("106.805 cm", font, fontsize)
    moment_right_offset = stringWidth("Momentx", font, fontsize)  # same as above
    x = (arm_x + weight_x + weight_right_offset) // 2  # multiply symbol position
    eq = moment_x - 20  # equal symbol position

    # Start writing the W&B table
    start = 685  # starting y
    pdf.drawString(weight_x, start, "Empty Weight")
    pdf.drawString(arm_x, start, "Arm")
    pdf.drawString(moment_x, start, "Moment")
    start -= newline
    pdf.drawRightString(
        weight_x + weight_right_offset, start, f"{plane.empty_mass_kg} kg"
    )
    pdf.drawString(x, start, "x")
    pdf.drawRightString(arm_x + arm_right_offset, start, f"{plane.empty_arm_cm} cm")
    pdf.drawString(eq, start, "=")
    pdf.drawRightString(moment_x + moment_right_offset, start, str(plane.empty_moment))
    start -= newline

    # Start writing the load
    pdf.setFont("Helvetica-Bold", fontsize)
    _underline(pdf, weight_x // 2, start, "Load", "Helvetica-Bold", fontsize)
    pdf.setFont(font, fontsize)
    start -= newline
    for station, weights in plane.loading.items():
        arm = plane.arms[station]
        station = _sanitize_station(station)
        pdf.drawString(weight_x // 2, start, station)
        for name, weight in weights.items():
            weight = round(weight, 2)
            arm = round(arm, 2)
            start -= newline
            pdf.drawString(weight_x // 2, start, f"  – {name}")
            pdf.drawRightString(weight_x + weight_right_offset, start, f"{weight} kg")
            pdf.drawString(x, start, "x")
            pdf.drawRightString(arm_x + arm_right_offset, start, f"{arm} cm")
            pdf.drawString(eq, start, "=")
            pdf.drawRightString(
                moment_x + moment_right_offset, start, str(round(weight * arm, 2))
            )
        start -= newline + 10

    # Write the totals at the bottom
    pdf.setFont("Helvetica-Bold", fontsize)
    pdf.drawString(weight_x // 2, start, "Totals")
    pdf.line(
        weight_x // 2,
        start - 2,
        moment_x + stringWidth("Moment", font, fontsize),
        start - 2,
    )
    pdf.setFont(font, fontsize)
    start -= newline
    pdf.drawRightString(
        weight_x + weight_right_offset, start, f"Weight: {plane.total_weight()} kg"
    )
    pdf.drawRightString(
        moment_x + moment_right_offset, start, f"Moment: {plane.total_moment()}"
    )
    start -= newline
    shift = stringWidth(f"Weight", font, fontsize)
    pdf.drawRightString(weight_x + shift, start, f"CoG: {plane.CoG()}")

    # Add the graph
    graph_path = "./wb_c172s.png"
    scale = 2.3  # scale of the image; DO NOT CHANGE THIS otherwise the lines will be broken!
    pdf.drawImage(
        graph_path,
        width // 2,  # DO NOT CHANGE THIS
        start - 190,  # DO NOT CHANGE THIS
        width=width // scale,
        height=height // scale,
        anchorAtXY=True,
        anchor="c",
    )

    # Draw lines onto the chart
    # This works by mapping a high and low value on the chart to their
    # corresponding high and low values in pixels, then mapping between the two.
    def CoG_horizontal_line_height(val):
        """Get the pixel height of the line, in relation to how far down it is in the *image*."""
        return start - val

    # With fuel
    pdf.setStrokeColor("black")
    pdf.setLineWidth(1.25)
    start -= 50  # should put a little nub into the x axis ticks above
    vert = _map2range(plane.CoG() * CM2MM, 1225, 875, 384.25, 212)
    pdf.line(vert, start, vert, start - 285)
    h_factor = _map2range(plane.total_weight(), 1050, 650, 49.75, 275)
    pdf.line(
        200,
        CoG_horizontal_line_height(h_factor),
        400,
        CoG_horizontal_line_height(h_factor),
    )

    # Without fuel
    pdf.setStrokeColor("red")
    vert = _map2range(plane.CoG(with_fuel=False) * CM2MM, 1225, 875, 384.25, 212)
    pdf.line(vert, start, vert, start - 285)
    h_factor = _map2range(plane.total_weight(with_fuel=False), 1050, 650, 49.75, 275)
    pdf.line(
        200,
        CoG_horizontal_line_height(h_factor),
        400,
        CoG_horizontal_line_height(h_factor),
    )

    # Legend/disclaimer notice
    start = 70 + newline
    pdf.setFillColorRGB(1, 0, 0)
    disclaimer_fontsize = fontsize / 2
    pdf.setFont("Helvetica", disclaimer_fontsize)
    label_width = stringWidth("Red line", "Helvetica", disclaimer_fontsize)
    pdf.drawString(50, start, "Red line")
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(50 + label_width, start, ": no usable fuel")
    pdf.drawString(50, start - newline / 2, "Black line: with fuel")
    pdf.setFont("Helvetica-Oblique", fontsize / 2)
    pdf.drawString(50, start - newline - newline / 2, "Double check graph for accuracy")

    pdf.save()


if __name__ == "__main__":
    wb_file = "weight_and_balance.json"
    if os.path.exists(wb_file):
        with open(wb_file, "r") as f:
            config = json.load(f)
    else:
        print("\nC172 Weight and Balance PDF Generator")
        print("\nAdd weights to `wb.json`. Weights are in kilograms, fuel in liters.")
        sys.exit(0)

    # Create the plane
    plane = C172S_WB(config["plane"])

    # Load it
    for station in [
        STATIONS.FRONT_SEATS,
        STATIONS.FRONT_BAGGAGE,
        STATIONS.BACK_SEATS,
        STATIONS.BACK_BAGGAGE,
    ]:
        station_cfg = config[station]
        for item, weight in station_cfg.items():
            plane.load(weight, station, item)

    plane.fuel(config["fuel"])

    # Create the pdf
    create_pdf(plane)
