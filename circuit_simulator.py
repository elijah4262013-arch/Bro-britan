#!/usr/bin/env python3
"""
⚡ ELECTRONIC CIRCUIT SIMULATOR ⚡
Build, test, and debug electronic circuits in real-time!
Learn about resistors, capacitors, LEDs, batteries, and more.
"""

import math
import time
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ComponentType(Enum):
    """Types of electronic components"""
    RESISTOR = "Resistor"
    CAPACITOR = "Capacitor"
    LED = "LED"
    BATTERY = "Battery"
    SWITCH = "Switch"
    AMMETER = "Ammeter"
    VOLTMETER = "Voltmeter"
    WIRE = "Wire"


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

    def __str__(self):
        return f"{self.name} ({self.component_type.value}) | {abs(self.voltage):.2f}V | {self.current:.3f}A"


class Resistor(Component):
    """Resistor component (Ohm's Law: V = IR)"""
    
    def __init__(self, name: str, resistance: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.RESISTOR, node_a, node_b)
        self.resistance = resistance  # Ohms
        self.power_dissipated = 0.0  # Watts

    def calculate_voltage(self):
        """V = IR"""
        self.voltage = self.current * self.resistance
        self.power_dissipated = self.current ** 2 * self.resistance

    def __str__(self):
        return f"{self.name} ({self.resistance}Ω) | {abs(self.voltage):.2f}V | {self.current:.3f}A | Power: {self.power_dissipated:.3f}W"


class Capacitor(Component):
    """Capacitor component (stores charge)"""
    
    def __init__(self, name: str, capacitance: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.CAPACITOR, node_a, node_b)
        self.capacitance = capacitance  # Farads
        self.charge = 0.0  # Coulombs

    def calculate_charge(self):
        """Q = CV"""
        self.charge = self.capacitance * self.voltage

    def __str__(self):
        return f"{self.name} ({self.capacitance*1e6:.1f}μF) | {abs(self.voltage):.2f}V | Charge: {self.charge*1e9:.2f}nC"


class LED(Component):
    """LED component (light emitting diode)"""
    
    def __init__(self, name: str, forward_voltage: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.LED, node_a, node_b)
        self.forward_voltage = forward_voltage  # Typically 2V
        self.brightness = 0  # 0-100%
        self.max_current = 0.020  # 20mA safe operating current
        self.is_burning = False

    def update_brightness(self):
        """Update LED brightness based on current"""
        if self.current > 0.001:  # Threshold for LED to turn on
            self.brightness = min(100, (self.current / self.max_current) * 100)
            if self.current > self.max_current:
                self.is_burning = True
        else:
            self.brightness = 0
            self.is_burning = False

    def __str__(self):
        status = "🔥 BURNING!" if self.is_burning else ("💡 ON" if self.brightness > 0 else "⚫ OFF")
        return f"{self.name} | {self.brightness:.0f}% brightness | {status} | {self.current*1000:.1f}mA"


class Battery(Component):
    """Battery component (voltage source)"""
    
    def __init__(self, name: str, voltage: float, node_a: int, node_b: int):
        super().__init__(name, ComponentType.BATTERY, node_a, node_b)
        self.emf = voltage  # Electromotive force
        self.internal_resistance = 0.1  # Ohms
        self.voltage = voltage

    def __str__(self):
        return f"{self.name} ({self.emf}V Battery) | Output: {self.voltage:.2f}V | {self.current:.3f}A"


class Switch(Component):
    """Switch component (open/closed circuit)"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.SWITCH, node_a, node_b)
        self.is_closed = False  # False = open, True = closed
        self.resistance = 1e6 if not self.is_closed else 0.001  # High resistance when open

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
        self.resistance = 0.001  # Ammeter has very low resistance

    def __str__(self):
        return f"{self.name} (Ammeter) | {self.current*1000:.2f}mA"


class Voltmeter(Component):
    """Voltmeter component (measures voltage)"""
    
    def __init__(self, name: str, node_a: int, node_b: int):
        super().__init__(name, ComponentType.VOLTMETER, node_a, node_b)
        self.resistance = 1e9  # Voltmeter has very high resistance

    def __str__(self):
        return f"{self.name} (Voltmeter) | {abs(self.voltage):.2f}V"


class Circuit:
    """Main circuit simulator"""
    
    def __init__(self):
        self.components: List[Component] = []
        self.nodes: Dict[int, List[Component]] = {}
        self.voltages: Dict[int, float] = {}  # Node voltages
        self.time = 0.0
        self.is_running = False

    def add_component(self, component: Component):
        """Add component to circuit"""
        self.components.append(component)
        
        # Track which components connect to each node
        if component.node_a not in self.nodes:
            self.nodes[component.node_a] = []
        if component.node_b not in self.nodes:
            self.nodes[component.node_b] = []
        
        self.nodes[component.node_a].append(component)
        self.nodes[component.node_b].append(component)
        
        print(f"✅ Added {component.name}")

    def remove_component(self, name: str) -> bool:
        """Remove component from circuit"""
        for comp in self.components:
            if comp.name.lower() == name.lower():
                self.components.remove(comp)
                print(f"✅ Removed {comp.name}")
                return True
        print("❌ Component not found!")
        return False

    def simulate_step(self):
        """Execute one simulation step using simplified circuit analysis"""
        if not self.components:
            return

        # Find battery (voltage source)
        battery = None
        for comp in self.components:
            if isinstance(comp, Battery):
                battery = comp
                break

        if not battery or not battery.active:
            return

        # Simple series circuit analysis
        total_resistance = 0.0
        total_voltage = battery.emf

        for comp in self.components:
            if isinstance(comp, Battery):
                continue
            
            if isinstance(comp, Resistor):
                total_resistance += comp.resistance
            elif isinstance(comp, Switch):
                total_resistance += comp.resistance
            elif isinstance(comp, Ammeter):
                total_resistance += comp.resistance

        # Calculate current (Ohm's Law: I = V/R)
        if total_resistance > 0:
            current = total_voltage / total_resistance
        else:
            current = 0

        # Update all components
        for comp in self.components:
            comp.current = current if battery.active else 0

        # Calculate voltages across components
        voltage_drop = 0
        for comp in self.components:
            if isinstance(comp, Resistor):
                comp.calculate_voltage()
            elif isinstance(comp, LED):
                comp.voltage = comp.forward_voltage
                comp.update_brightness()
            elif isinstance(comp, Capacitor):
                comp.voltage = total_voltage - voltage_drop
                comp.calculate_charge()
            elif isinstance(comp, Battery):
                comp.voltage = battery.emf

            if isinstance(comp, Resistor) or isinstance(comp, Switch):
                voltage_drop += comp.voltage

        self.time += 0.001  # 1ms steps

    def display_status(self):
        """Display circuit status"""
        print("\n" + "="*80)
        print("⚡ CIRCUIT STATUS")
        print("="*80)
        
        if not self.components:
            print("Circuit is empty!")
        else:
            for comp in self.components:
                print(f"  {comp}")
        
        print("="*80)

    def display_circuit_info(self):
        """Display detailed circuit information"""
        print("\n" + "="*80)
        print("📊 CIRCUIT ANALYSIS")
        print("="*80)
        
        # Find batteries
        batteries = [c for c in self.components if isinstance(c, Battery)]
        resistors = [c for c in self.components if isinstance(c, Resistor)]
        leds = [c for c in self.components if isinstance(c, LED)]
        
        if batteries:
            total_emf = sum(b.emf for b in batteries)
            print(f"\n🔋 Batteries:")
            print(f"   Total EMF: {total_emf}V")
            for b in batteries:
                print(f"   - {b}")
        
        if resistors:
            total_resistance = sum(r.resistance for r in resistors)
            total_power = sum(r.power_dissipated for r in resistors)
            print(f"\n⚛️  Resistors:")
            print(f"   Total Resistance: {total_resistance}Ω")
            print(f"   Total Power Dissipated: {total_power:.3f}W")
            for r in resistors:
                print(f"   - {r}")
        
        if leds:
            print(f"\n💡 LEDs:")
            for led in leds:
                print(f"   - {led}")
        
        print("="*80)


def get_component_value(prompt: str, component_type: str) -> float:
    """Get user input for component values"""
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("❌ Value must be positive!")
                continue
            return value
        except ValueError:
            print("❌ Please enter a valid number!")


def main():
    """Main simulator interface"""
    print("\n" + "="*80)
    print("⚡ WELCOME TO ELECTRONIC CIRCUIT SIMULATOR ⚡")
    print("="*80)
    print("\nBuild and simulate real electronic circuits!")
    print("Learn about current, voltage, resistance, and power!")
    
    circuit = Circuit()
    running = True

    print("\n📚 Available Commands:")
    print("  add-battery      - Add a battery (voltage source)")
    print("  add-resistor     - Add a resistor")
    print("  add-led          - Add an LED")
    print("  add-capacitor    - Add a capacitor")
    print("  add-switch       - Add a switch")
    print("  add-ammeter      - Add an ammeter (current meter)")
    print("  add-voltmeter    - Add a voltmeter (voltage meter)")
    print("  toggle-switch    - Toggle a switch open/closed")
    print("  remove           - Remove a component")
    print("  status           - Show circuit status")
    print("  analyze          - Detailed circuit analysis")
    print("  simulate         - Run simulation (100 steps)")
    print("  list             - List all components")
    print("  clear            - Clear circuit")
    print("  quit             - Exit simulator")

    # Create a sample circuit
    sample = input("\n🎮 Would you like to load a sample circuit? (y/n): ").lower() == "y"
    
    if sample:
        print("\n📦 Loading sample circuit: LED circuit with resistor...")
        circuit.add_component(Battery("BAT1", 5.0, 0, 1))
        circuit.add_component(Resistor("R1", 220, 1, 2))  # Current limiting resistor
        circuit.add_component(LED("LED1", 2.0, 2, 0))
        circuit.add_component(Ammeter("A1", 0, 1))
        circuit.display_status()

    while running:
        command = input("\n> ").lower().strip()

        if command == "add-battery":
            name = input("Battery name: ")
            voltage = get_component_value("Voltage (V): ", "battery")
            circuit.add_component(Battery(name, voltage, 0, 1))

        elif command == "add-resistor":
            name = input("Resistor name: ")
            resistance = get_component_value("Resistance (Ω): ", "resistor")
            circuit.add_component(Resistor(name, resistance, 1, 2))

        elif command == "add-led":
            name = input("LED name: ")
            circuit.add_component(LED(name, 2.0, 2, 0))

        elif command == "add-capacitor":
            name = input("Capacitor name: ")
            capacitance = get_component_value("Capacitance (F): ", "capacitor")
            circuit.add_component(Capacitor(name, capacitance, 1, 0))

        elif command == "add-switch":
            name = input("Switch name: ")
            circuit.add_component(Switch(name, 1, 2))

        elif command == "add-ammeter":
            name = input("Ammeter name: ")
            circuit.add_component(Ammeter(name, 0, 1))

        elif command == "add-voltmeter":
            name = input("Voltmeter name: ")
            circuit.add_component(Voltmeter(name, 1, 2))

        elif command == "toggle-switch":
            name = input("Switch name: ")
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
            name = input("Component name: ")
            circuit.remove_component(name)

        elif command == "status":
            circuit.display_status()

        elif command == "analyze":
            circuit.display_circuit_info()

        elif command == "simulate":
            print("🔄 Running simulation...")
            for _ in range(100):
                circuit.simulate_step()
            print("✅ Simulation complete!")
            circuit.display_status()

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
            print("🗑️  Circuit cleared!")

        elif command == "quit":
            running = False
            print("\n👋 Thanks for using the Circuit Simulator!")

        else:
            print("❌ Unknown command! Type 'help' for commands.")


if __name__ == "__main__":
    main()
