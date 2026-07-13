#!/usr/bin/env python3
"""
⚡ ADVANCED ELECTRONIC CIRCUIT SIMULATOR ⚡
Professional-grade circuit simulation with AC/DC, transistors, transformers, 
rectifiers, and real-time graphical visualization!
"""

import math
import time
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
from collections import deque

# Try to import matplotlib for visualization
try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib not available. Install with: pip install matplotlib")


class ComponentType(Enum):
    """Types of electronic components"""
    RESISTOR = "Resistor"
    CAPACITOR = "Capacitor"
    INDUCTOR = "Inductor"
    LED = "LED"
    BATTERY = "Battery"
    AC_SOURCE = "AC Source"
    SWITCH = "Switch"
    AMMETER = "Ammeter"
    VOLTMETER = "Voltmeter"
    BJT_NPN = "BJT NPN Transistor"
    BJT_PNP = "BJT PNP Transistor"
    FET_N = "N-Channel FET"
    FET_P = "P-Channel FET"
    TRANSFORMER = "Transformer"
    DIODE = "Diode"
    BRIDGE_RECTIFIER = "Bridge Rectifier"


class Component:
    """Base class for electronic components"""
    
    def __init__(self, name: str, component_type: ComponentType, node_a: int, node_b: int):
        self.name = name
        self.component_type = component_type
        self.node_a = node_a
        self.node_b = node_b
        self.current = 0.0  # Amperes
        self.voltage = 0.0  # Volts
        self.active = True
        self.history = deque(maxlen=1000)  # Store history for plotting

    def record_history(self):
        """Record current state for plotting"""
        try:
            self.history.append((float(self.voltage), float(self.current)))
        except (ValueError, TypeError):
            self.history.append((0.0, 0.0))

    def __str__(self):
        return f"{self.name} ({self.component_type.value}) | {abs(self.voltage):.2f}V | {self.current:.3f}A"


class Resistor(Component):
    """Resistor component (Ohm's Law: V = IR)"""
    
    def __init__(self, name: str, resistance: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.RESISTOR, node_a, node_b)
        self.resistance = max(0.001, float(resistance))  # Avoid zero/negative resistance
        self.power_dissipated = 0.0  # Watts

    def calculate_voltage(self):
        """V = IR"""
        self.voltage = self.current * self.resistance
        self.power_dissipated = abs(self.current ** 2 * self.resistance)

    def __str__(self):
        return f"{self.name} ({self.resistance}Ω) | {abs(self.voltage):.2f}V | {self.current:.3f}A | Power: {self.power_dissipated:.3f}W"


class Capacitor(Component):
    """Capacitor component (stores charge, blocks DC, passes AC)"""
    
    def __init__(self, name: str, capacitance: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.CAPACITOR, node_a, node_b)
        self.capacitance = max(1e-12, float(capacitance))  # Avoid zero capacitance
        self.charge = 0.0  # Coulombs
        self.previous_voltage = 0.0

    def calculate_impedance_ac(self, frequency: float) -> float:
        """Capacitive reactance: Xc = 1/(2πfC)"""
        if frequency <= 0:
            return 1e9  # Blocks DC
        try:
            return 1.0 / (2 * math.pi * frequency * self.capacitance)
        except (ZeroDivisionError, ValueError):
            return 1e9

    def __str__(self):
        return f"{self.name} ({self.capacitance*1e6:.1f}μF) | {abs(self.voltage):.2f}V | Charge: {self.charge*1e9:.2f}nC"


class Inductor(Component):
    """Inductor component (opposes current changes)"""
    
    def __init__(self, name: str, inductance: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.INDUCTOR, node_a, node_b)
        self.inductance = max(1e-9, float(inductance))  # Avoid zero inductance
        self.previous_current = 0.0

    def calculate_impedance_ac(self, frequency: float) -> float:
        """Inductive reactance: Xl = 2πfL"""
        try:
            return 2 * math.pi * frequency * self.inductance
        except (ValueError, OverflowError):
            return 0.0

    def __str__(self):
        return f"{self.name} ({self.inductance*1000:.1f}mH) | {abs(self.voltage):.2f}V | {self.current:.3f}A"


class LED(Component):
    """LED component (light emitting diode)"""
    
    def __init__(self, name: str, forward_voltage: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.LED, node_a, node_b)
        self.forward_voltage = float(forward_voltage)
        self.brightness = 0.0
        self.max_current = 0.020
        self.is_burning = False

    def update_brightness(self):
        """Update LED brightness based on current"""
        try:
            if abs(self.current) > 0.001:
                self.brightness = min(100.0, (abs(self.current) / self.max_current) * 100)
                if abs(self.current) > self.max_current:
                    self.is_burning = True
                else:
                    self.is_burning = False
            else:
                self.brightness = 0.0
                self.is_burning = False
        except (ValueError, ZeroDivisionError):
            self.brightness = 0.0
            self.is_burning = False

    def __str__(self):
        status = "🔥 BURNING!" if self.is_burning else ("💡 ON" if self.brightness > 0 else "⚫ OFF")
        return f"{self.name} | {self.brightness:.0f}% brightness | {status} | {self.current*1000:.1f}mA"


class Battery(Component):
    """DC Battery (constant voltage source)"""
    
    def __init__(self, name: str, voltage: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.BATTERY, node_a, node_b)
        self.emf = float(voltage)
        self.internal_resistance = 0.1
        self.voltage = self.emf

    def __str__(self):
        return f"{self.name} ({self.emf}V Battery) | Output: {self.voltage:.2f}V | {self.current:.3f}A"


class ACSource(Component):
    """AC Voltage Source (sinusoidal)"""
    
    def __init__(self, name: str, amplitude: float, frequency: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.AC_SOURCE, node_a, node_b)
        self.amplitude = float(amplitude)
        self.frequency = max(0.1, float(frequency))  # Avoid zero frequency
        self.phase = 0.0  # Radians
        self.time = 0.0
        self.rms_voltage = self.amplitude / math.sqrt(2)

    def calculate_voltage(self, time: float):
        """V(t) = A * sin(2πft + φ)"""
        try:
            self.voltage = self.amplitude * math.sin(2 * math.pi * self.frequency * time + self.phase)
            self.time = time
        except (ValueError, OverflowError):
            self.voltage = 0.0

    def __str__(self):
        return f"{self.name} ({self.amplitude:.1f}V peak @ {self.frequency}Hz) | RMS: {self.rms_voltage:.2f}V | {self.current:.3f}A"


class Switch(Component):
    """Switch component (open/closed circuit)"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.SWITCH, node_a, node_b)
        self.is_closed = False
        self.resistance = 1e6 if not self.is_closed else 0.001

    def toggle(self):
        """Toggle switch state"""
        self.is_closed = not self.is_closed
        self.resistance = 0.001 if self.is_closed else 1e6

    def __str__(self):
        status = "🔴 CLOSED" if self.is_closed else "🟢 OPEN"
        return f"{self.name} | {status} | {self.current:.3f}A"


class Ammeter(Component):
    """Ammeter component (measures current)"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.AMMETER, node_a, node_b)
        self.resistance = 0.001

    def __str__(self):
        return f"{self.name} (Ammeter) | {abs(self.current)*1000:.2f}mA"


class Voltmeter(Component):
    """Voltmeter component (measures voltage)"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.VOLTMETER, node_a, node_b)
        self.resistance = 1e9

    def __str__(self):
        return f"{self.name} (Voltmeter) | {abs(self.voltage):.2f}V"


class Diode(Component):
    """Diode - one-way valve for electricity"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.DIODE, node_a, node_b)
        self.forward_voltage = 0.7
        self.is_conducting = False

    def check_conduction(self):
        """Diode conducts if forward biased"""
        self.is_conducting = self.voltage > self.forward_voltage and self.current > 0

    def __str__(self):
        status = "✅ CONDUCTING" if self.is_conducting else "❌ BLOCKING"
        return f"{self.name} (Diode) | {status} | {self.current:.3f}A"


class Transformer(Component):
    """Transformer - changes AC voltage via inductive coupling"""
    
    def __init__(self, name: str, primary_turns: int, secondary_turns: int, node_a: int, node_b: int):
        super().__init__(name, ComponentType.TRANSFORMER, node_a, node_b)
        self.primary_turns = max(1, int(primary_turns))
        self.secondary_turns = max(1, int(secondary_turns))
        self.ratio = self.secondary_turns / self.primary_turns
        self.primary_voltage = 0.0
        self.secondary_voltage = 0.0
        self.primary_current = 0.0
        self.secondary_current = 0.0
        self.efficiency = 0.95

    def transform_voltage(self, primary_voltage: float):
        """Secondary voltage = Primary voltage × (N2/N1)"""
        try:
            self.primary_voltage = float(primary_voltage)
            self.secondary_voltage = primary_voltage * self.ratio * self.efficiency
        except (ValueError, OverflowError):
            self.secondary_voltage = 0.0

    def transform_current(self, primary_current: float):
        """Current ratio = N1/N2 (inverse of voltage)"""
        try:
            self.primary_current = float(primary_current)
            self.secondary_current = primary_current / (self.ratio + 0.001)
        except (ValueError, ZeroDivisionError):
            self.secondary_current = 0.0

    def __str__(self):
        return f"{self.name} (Transformer {self.primary_turns}:{self.secondary_turns}) | Primary: {self.primary_voltage:.2f}V @ {self.primary_current:.3f}A | Secondary: {self.secondary_voltage:.2f}V @ {self.secondary_current:.3f}A"


class BridgeRectifier(Component):
    """Full-wave bridge rectifier - converts AC to DC"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.BRIDGE_RECTIFIER, node_a, node_b)
        self.diode_forward_voltage = 0.7
        self.is_conducting = False
        self.output_voltage = 0.0

    def rectify(self, input_voltage: float):
        """Full-wave rectification: outputs absolute value minus diode drops"""
        try:
            voltage_drop = 2 * self.diode_forward_voltage
            
            if abs(input_voltage) > voltage_drop:
                self.output_voltage = abs(input_voltage) - voltage_drop
                self.is_conducting = True
            else:
                self.output_voltage = 0.0
                self.is_conducting = False
            
            self.voltage = self.output_voltage
        except (ValueError, TypeError):
            self.output_voltage = 0.0
            self.is_conducting = False

    def __str__(self):
        status = "✅ RECTIFYING" if self.is_conducting else "❌ BLOCKED"
        return f"{self.name} (Bridge Rectifier) | {status} | Output: {self.output_voltage:.2f}V | {self.current:.3f}A"


class BJTTransistor(Component):
    """Bipolar Junction Transistor (NPN or PNP)"""
    
    def __init__(self, name: str, transistor_type: str, node_c: int, node_b: int, node_e: int):
        component_type = ComponentType.BJT_NPN if transistor_type == "NPN" else ComponentType.BJT_PNP
        super().__init__(name, component_type, node_c, node_b)
        self.node_e = node_e
        self.transistor_type = transistor_type
        self.base_current = 0.0
        self.collector_current = 0.0
        self.emitter_current = 0.0
        self.beta = 100
        self.base_threshold = 0.7
        self.is_saturated = False

    def update_currents(self, vbe: float, vce_sat: float = 0.2):
        """Update transistor currents based on voltages"""
        try:
            if vbe > self.base_threshold:
                self.collector_current = min(abs(self.base_current) * self.beta, 0.5)
                self.is_saturated = True
            else:
                self.collector_current = 0.0
                self.is_saturated = False
            
            self.emitter_current = self.collector_current + self.base_current
        except (ValueError, TypeError):
            self.collector_current = 0.0
            self.is_saturated = False

    def __str__(self):
        status = "🟢 ON" if self.is_saturated else "⚫ OFF"
        return f"{self.name} (BJT {self.transistor_type}) | {status} | Ic: {self.collector_current*1000:.1f}mA | β: {self.beta}"


class FETTransistor(Component):
    """Field Effect Transistor (N-Channel or P-Channel)"""
    
    def __init__(self, name: str, transistor_type: str, node_d: int, node_g: int, node_s: int):
        component_type = ComponentType.FET_N if transistor_type == "N" else ComponentType.FET_P
        super().__init__(name, component_type, node_d, node_g)
        self.node_s = node_s
        self.transistor_type = transistor_type
        self.gate_voltage = 0.0
        self.drain_current = 0.0
        self.vth = 2.0
        self.transconductance = 0.1

    def calculate_drain_current(self, vgs: float, vds: float):
        """Calculate drain current based on gate-source voltage"""
        try:
            if (self.transistor_type == "N" and vgs > self.vth) or (self.transistor_type == "P" and vgs < -self.vth):
                self.drain_current = self.transconductance * (abs(vgs) - self.vth)
            else:
                self.drain_current = 0.0
        except (ValueError, TypeError):
            self.drain_current = 0.0

    def __str__(self):
        status = "🟢 ON" if self.drain_current > 0 else "⚫ OFF"
        return f"{self.name} (FET {self.transistor_type}-Channel) | {status} | Id: {self.drain_current*1000:.1f}mA"


class Circuit:
    """Advanced circuit simulator with AC/DC support"""
    
    def __init__(self):
        self.components: List[Component] = []
        self.nodes: Dict[int, List[Component]] = {}
        self.time = 0.0
        self.frequency = 60
        self.simulation_running = False
        self.time_step = 0.0001

    def add_component(self, component: Component):
        """Add component to circuit"""
        if component is None:
            print("❌ Cannot add None component!")
            return
            
        self.components.append(component)
        
        if component.node_a not in self.nodes:
            self.nodes[component.node_a] = []
        if component.node_b not in self.nodes:
            self.nodes[component.node_b] = []
        
        self.nodes[component.node_a].append(component)
        self.nodes[component.node_b].append(component)
        
        print(f"✅ Added {component.name}")

    def remove_component(self, name: str) -> bool:
        """Remove component from circuit"""
        for comp in self.components[:]:  # Iterate over copy
            if comp.name.lower() == name.lower():
                self.components.remove(comp)
                print(f"✅ Removed {comp.name}")
                return True
        print("❌ Component not found!")
        return False

    def simulate_step(self):
        """Execute one simulation step with AC support"""
        if not self.components:
            return

        try:
            # Update AC sources
            for comp in self.components:
                if isinstance(comp, ACSource):
                    comp.calculate_voltage(self.time)

            # Simple circuit analysis
            total_resistance = 0.0
            total_impedance = 0.0
            total_voltage = 0.0
            has_ac = any(isinstance(c, ACSource) for c in self.components)

            for comp in self.components:
                if isinstance(comp, Battery):
                    total_voltage += comp.emf
                elif isinstance(comp, ACSource):
                    total_voltage += comp.voltage
                elif isinstance(comp, Resistor):
                    total_resistance += comp.resistance
                elif isinstance(comp, Switch):
                    total_resistance += comp.resistance
                elif isinstance(comp, Ammeter):
                    total_resistance += comp.resistance
                elif isinstance(comp, Inductor):
                    if has_ac:
                        impedance = comp.calculate_impedance_ac(self.frequency)
                        total_impedance += impedance if impedance > 0 else 0
                elif isinstance(comp, Capacitor):
                    if has_ac:
                        impedance = comp.calculate_impedance_ac(self.frequency)
                        total_impedance += impedance if impedance > 0 else 0

            # Calculate current using impedance for AC circuits
            total_z = total_resistance + total_impedance if has_ac else total_resistance
            
            if total_z > 0:
                current = total_voltage / total_z
            else:
                current = 0

            # Update all components
            for comp in self.components:
                if comp.active:
                    comp.current = current
                else:
                    comp.current = 0

            # Calculate component-specific behavior
            for comp in self.components:
                if isinstance(comp, Resistor):
                    comp.calculate_voltage()
                elif isinstance(comp, LED):
                    comp.voltage = comp.forward_voltage
                    comp.update_brightness()
                elif isinstance(comp, Capacitor):
                    impedance = comp.calculate_impedance_ac(self.frequency) if self.frequency > 0 else 1e9
                    comp.voltage = current * impedance if impedance > 0 else 0
                elif isinstance(comp, Transformer):
                    ac_source = next((c for c in self.components if isinstance(c, ACSource)), None)
                    if ac_source:
                        comp.transform_voltage(ac_source.voltage)
                        comp.transform_current(current)
                elif isinstance(comp, BridgeRectifier):
                    ac_source = next((c for c in self.components if isinstance(c, ACSource)), None)
                    if ac_source:
                        comp.rectify(ac_source.voltage)

                comp.record_history()

            self.time += self.time_step
            
        except Exception as e:
            print(f"⚠️  Simulation step error: {e}")

    def display_status(self):
        """Display circuit status"""
        print("\n" + "="*100)
        print("⚡ CIRCUIT STATUS")
        print("="*100)
        
        if not self.components:
            print("Circuit is empty!")
        else:
            for comp in self.components:
                print(f"  {comp}")
        
        print(f"\nSimulation Time: {self.time:.6f}s | Time Step: {self.time_step*1e6:.1f}µs")
        print("="*100)

    def display_circuit_info(self):
        """Display detailed circuit analysis"""
        print("\n" + "="*100)
        print("📊 CIRCUIT ANALYSIS")
        print("="*100)
        
        batteries = [c for c in self.components if isinstance(c, Battery)]
        ac_sources = [c for c in self.components if isinstance(c, ACSource)]
        resistors = [c for c in self.components if isinstance(c, Resistor)]
        capacitors = [c for c in self.components if isinstance(c, Capacitor)]
        inductors = [c for c in self.components if isinstance(c, Inductor)]
        transformers = [c for c in self.components if isinstance(c, Transformer)]
        rectifiers = [c for c in self.components if isinstance(c, BridgeRectifier)]
        transistors = [c for c in self.components if isinstance(c, (BJTTransistor, FETTransistor))]
        
        if batteries:
            total_emf = sum(b.emf for b in batteries)
            print(f"\n🔋 DC Batteries:")
            print(f"   Total EMF: {total_emf}V")
            for b in batteries:
                print(f"   - {b}")
        
        if ac_sources:
            print(f"\n〰️  AC Sources:")
            for ac in ac_sources:
                print(f"   - {ac}")
                print(f"     Frequency: {ac.frequency}Hz | Period: {1/max(ac.frequency, 0.1)*1000:.2f}ms")
        
        if resistors:
            total_resistance = sum(r.resistance for r in resistors)
            total_power = sum(abs(r.power_dissipated) for r in resistors)
            print(f"\n⚛️  Resistors:")
            print(f"   Total Resistance: {total_resistance}Ω")
            print(f"   Total Power Dissipated: {total_power:.3f}W")
            for r in resistors:
                print(f"   - {r}")
        
        if capacitors:
            print(f"\n🔋 Capacitors:")
            for c in capacitors:
                print(f"   - {c}")
        
        if inductors:
            print(f"\n📈 Inductors:")
            for l in inductors:
                print(f"   - {l}")
        
        if transformers:
            print(f"\n⚙️  Transformers:")
            for t in transformers:
                print(f"   - {t}")
        
        if rectifiers:
            print(f"\n🔧 Bridge Rectifiers:")
            for r in rectifiers:
                print(f"   - {r}")
        
        if transistors:
            print(f"\n🔌 Transistors:")
            for t in transistors:
                print(f"   - {t}")
        
        print("="*100)

    def plot_waveforms(self, component_names: List[str] = None):
        """Plot voltage and current waveforms"""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib not available!")
            return
        
        if component_names is None:
            component_names = [c.name for c in self.components[:3] if len(c.history) > 0]
        
        if not component_names:
            print("❌ No components with history to plot!")
            return
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        
        for name in component_names:
            comp = next((c for c in self.components if c.name == name), None)
            if comp and len(comp.history) > 0:
                history = list(comp.history)
                voltages = [h[0] for h in history]
                currents = [h[1]*1000 for h in history]
                time_points = np.linspace(0, self.time, len(history))
                
                axes[0].plot(time_points, voltages, label=f"{comp.name} Voltage", marker='')
                axes[1].plot(time_points, currents, label=f"{comp.name} Current", marker='')
        
        axes[0].set_ylabel('Voltage (V)')
        axes[0].set_title('Component Voltages Over Time')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        axes[1].set_xlabel('Time (s)')
        axes[1].set_ylabel('Current (mA)')
        axes[1].set_title('Component Currents Over Time')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

    def export_data(self, filename: str = "circuit_data.txt"):
        """Export circuit data to file"""
        try:
            with open(filename, 'w') as f:
                f.write("="*80 + "\n")
                f.write("CIRCUIT SIMULATION DATA\n")
                f.write("="*80 + "\n\n")
                
                f.write(f"Simulation Time: {self.time:.6f}s\n")
                f.write(f"Components: {len(self.components)}\n\n")
                
                for comp in self.components:
                    f.write(f"{comp}\n")
                    if len(comp.history) > 0:
                        history = list(comp.history)
                        voltages = [h[0] for h in history]
                        currents = [h[1] for h in history]
                        
                        avg_voltage = sum(voltages) / len(voltages) if voltages else 0
                        max_voltage = max(voltages) if voltages else 0
                        min_voltage = min(voltages) if voltages else 0
                        avg_current = sum(currents) / len(currents) if currents else 0
                        max_current = max(currents) if currents else 0
                        
                        f.write(f"  Voltage - Avg: {avg_voltage:.3f}V, Max: {max_voltage:.3f}V, Min: {min_voltage:.3f}V\n")
                        f.write(f"  Current - Avg: {avg_current:.3f}A, Max: {max_current:.3f}A\n")
                    f.write("\n")
            
            print(f"✅ Data exported to {filename}")
        except Exception as e:
            print(f"❌ Error exporting data: {e}")


def get_component_value(prompt: str) -> float:
    """Get user input for component values with validation"""
    while True:
        try:
            user_input = input(prompt).strip()
            if not user_input:
                print("❌ Input cannot be empty!")
                continue
            
            value = float(user_input)
            if value <= 0:
                print("❌ Value must be positive!")
                continue
            return value
        except ValueError:
            print("❌ Please enter a valid number!")
        except KeyboardInterrupt:
            return 0.0


def main():
    """Main simulator interface"""
    print("\n" + "="*100)
    print("⚡ ADVANCED ELECTRONIC CIRCUIT SIMULATOR ⚡")
    print("="*100)
    print("\nProfessional-grade simulation: AC/DC, Transistors, Transformers, Rectifiers, Visualization!")
    
    circuit = Circuit()

    print("\n📚 Available Commands:")
    print("  === DC Components ===")
    print("  add-battery      - Add DC battery")
    print("  add-resistor     - Add resistor")
    print("  add-led          - Add LED")
    print("  add-switch       - Add switch")
    print("  === AC Components ===")
    print("  add-ac-source    - Add AC voltage source")
    print("  add-capacitor    - Add capacitor")
    print("  add-inductor     - Add inductor")
    print("  === Semiconductors ===")
    print("  add-diode        - Add diode")
    print("  add-bjt          - Add BJT transistor (NPN/PNP)")
    print("  add-fet          - Add FET transistor")
    print("  === Power Components ===")
    print("  add-transformer  - Add transformer")
    print("  add-rectifier    - Add full-wave bridge rectifier")
    print("  === Instruments ===")
    print("  add-ammeter      - Add ammeter (current meter)")
    print("  add-voltmeter    - Add voltmeter (voltage meter)")
    print("  === Circuit Control ===")
    print("  toggle-switch    - Toggle switch on/off")
    print("  remove           - Remove component")
    print("  list             - List all components")
    print("  clear            - Clear circuit")
    print("  === Simulation ===")
    print("  status           - Show circuit status")
    print("  analyze          - Detailed circuit analysis")
    print("  simulate         - Run simulation (100 steps)")
    print("  simulate-many    - Run extended simulation")
    print("  set-frequency    - Set AC frequency")
    print("  set-timestep     - Set simulation time step")
    print("  === Visualization ===")
    print("  plot             - Plot waveforms (requires matplotlib)")
    print("  export           - Export data to file")
    print("  quit             - Exit simulator")

    # Create a sample AC rectifier circuit
    sample = input("\n🎮 Load sample AC rectifier circuit? (y/n): ").lower() == "y"
    
    if sample:
        try:
            print("\n📦 Loading AC Rectifier with Transformer...")
            circuit.add_component(ACSource("AC1", 110, 60, 0, 1))
            circuit.add_component(Transformer("T1", 100, 20, 1, 2))
            circuit.add_component(BridgeRectifier("BR1", 2, 3))
            circuit.add_component(Capacitor("C1", 1000e-6, 3, 0))
            circuit.add_component(Resistor("R1", 100, 3, 0))
            circuit.add_component(Ammeter("A1", 0, 1))
            circuit.add_component(Voltmeter("V1", 2, 0))
            circuit.display_status()
        except Exception as e:
            print(f"❌ Error loading sample circuit: {e}")

    running = True
    while running:
        try:
            command = input("\n> ").lower().strip()

            if command == "add-battery":
                name = input("Battery name: ").strip()
                if not name:
                    name = f"BAT{len(circuit.components)}"
                voltage = get_component_value("Voltage (V): ")
                if voltage > 0:
                    circuit.add_component(Battery(name, voltage, 0, 1))

            elif command == "add-ac-source":
                name = input("Source name: ").strip()
                if not name:
                    name = f"AC{len(circuit.components)}"
                amplitude = get_component_value("Amplitude (V peak): ")
                frequency = get_component_value("Frequency (Hz): ")
                if amplitude > 0 and frequency > 0:
                    circuit.add_component(ACSource(name, amplitude, frequency, 0, 1))
                    circuit.frequency = frequency

            elif command == "add-resistor":
                name = input("Resistor name: ").strip()
                if not name:
                    name = f"R{len(circuit.components)}"
                resistance = get_component_value("Resistance (Ω): ")
                if resistance > 0:
                    circuit.add_component(Resistor(name, resistance, 1, 2))

            elif command == "add-capacitor":
                name = input("Capacitor name: ").strip()
                if not name:
                    name = f"C{len(circuit.components)}"
                capacitance = get_component_value("Capacitance (F, enter µF as 1e-6): ")
                if capacitance > 0:
                    circuit.add_component(Capacitor(name, capacitance, 1, 2))

            elif command == "add-inductor":
                name = input("Inductor name: ").strip()
                if not name:
                    name = f"L{len(circuit.components)}"
                inductance = get_component_value("Inductance (H, enter mH as 0.001): ")
                if inductance > 0:
                    circuit.add_component(Inductor(name, inductance, 1, 2))

            elif command == "add-led":
                name = input("LED name: ").strip()
                if not name:
                    name = f"LED{len(circuit.components)}"
                circuit.add_component(LED(name, 2.0, 2, 0))

            elif command == "add-diode":
                name = input("Diode name: ").strip()
                if not name:
                    name = f"D{len(circuit.components)}"
                circuit.add_component(Diode(name, 1, 2))

            elif command == "add-transformer":
                name = input("Transformer name: ").strip()
                if not name:
                    name = f"T{len(circuit.components)}"
                try:
                    primary = int(input("Primary turns: "))
                    secondary = int(input("Secondary turns: "))
                    if primary > 0 and secondary > 0:
                        circuit.add_component(Transformer(name, primary, secondary, 1, 2))
                except ValueError:
                    print("❌ Please enter valid integers for turns!")

            elif command == "add-rectifier":
                name = input("Rectifier name: ").strip()
                if not name:
                    name = f"BR{len(circuit.components)}"
                circuit.add_component(BridgeRectifier(name, 1, 0))

            elif command == "add-switch":
                name = input("Switch name: ").strip()
                if not name:
                    name = f"SW{len(circuit.components)}"
                circuit.add_component(Switch(name, 1, 2))

            elif command == "add-ammeter":
                name = input("Ammeter name: ").strip()
                if not name:
                    name = f"A{len(circuit.components)}"
                circuit.add_component(Ammeter(name, 0, 1))

            elif command == "add-voltmeter":
                name = input("Voltmeter name: ").strip()
                if not name:
                    name = f"V{len(circuit.components)}"
                circuit.add_component(Voltmeter(name, 1, 2))

            elif command == "add-bjt":
                name = input("Transistor name: ").strip()
                if not name:
                    name = f"Q{len(circuit.components)}"
                bjt_type = input("Type (NPN/PNP): ").upper().strip()
                if bjt_type in ["NPN", "PNP"]:
                    circuit.add_component(BJTTransistor(name, bjt_type, 1, 2, 0))
                else:
                    print("❌ Invalid type! Choose NPN or PNP")

            elif command == "add-fet":
                name = input("FET name: ").strip()
                if not name:
                    name = f"M{len(circuit.components)}"
                fet_type = input("Type (N/P for N-Channel/P-Channel): ").upper().strip()
                if fet_type in ["N", "P"]:
                    circuit.add_component(FETTransistor(name, fet_type, 1, 2, 0))
                else:
                    print("❌ Invalid type! Choose N or P")

            elif command == "toggle-switch":
                name = input("Switch name: ").strip()
                found = False
                for comp in circuit.components:
                    if isinstance(comp, Switch) and comp.name.lower() == name.lower():
                        comp.toggle()
                        status = "CLOSED ✅" if comp.is_closed else "OPEN 🟢"
                        print(f"Switch {name} is now {status}")
                        found = True
                        break
                if not found:
                    print("❌ Switch not found!")

            elif command == "remove":
                name = input("Component name: ").strip()
                circuit.remove_component(name)

            elif command == "status":
                circuit.display_status()

            elif command == "analyze":
                circuit.display_circuit_info()

            elif command == "simulate":
                print("🔄 Running simulation (100 steps)...")
                for _ in range(100):
                    circuit.simulate_step()
                print("✅ Simulation complete!")
                circuit.display_status()

            elif command == "simulate-many":
                try:
                    steps_input = input("Number of steps (default 10000): ").strip()
                    steps = int(steps_input) if steps_input else 10000
                    if steps > 0:
                        print(f"🔄 Running extended simulation ({steps} steps)...")
                        for _ in range(steps):
                            circuit.simulate_step()
                        print("✅ Simulation complete!")
                        circuit.display_status()
                except ValueError:
                    print("❌ Please enter a valid integer!")

            elif command == "set-frequency":
                freq = get_component_value("Frequency (Hz): ")
                if freq > 0:
                    circuit.frequency = freq
                    print(f"✅ Frequency set to {freq}Hz")

            elif command == "set-timestep":
                ts = get_component_value("Time step (seconds, e.g., 0.0001 for 100µs): ")
                if ts > 0:
                    circuit.time_step = ts
                    print(f"✅ Time step set to {ts*1e6:.1f}µs")

            elif command == "plot":
                if MATPLOTLIB_AVAILABLE:
                    circuit.plot_waveforms()
                else:
                    print("❌ matplotlib required! Install: pip install matplotlib")

            elif command == "export":
                filename = input("Filename (default: circuit_data.txt): ").strip()
                circuit.export_data(filename or "circuit_data.txt")

            elif command == "list":
                print("\n📋 Components in circuit:")
                if not circuit.components:
                    print("  Circuit is empty!")
                else:
                    for i, comp in enumerate(circuit.components, 1):
                        print(f"  {i}. {comp.name} ({comp.component_type.value})")

            elif command == "clear":
                circuit.components = []
                circuit.nodes = {}
                circuit.time = 0.0
                print("🗑️  Circuit cleared!")

            elif command == "quit":
                running = False
                print("\n👋 Thanks for using the Advanced Circuit Simulator!")

            else:
                print("❌ Unknown command!")

        except KeyboardInterrupt:
            print("\n\n👋 Exiting simulator...")
            running = False
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
