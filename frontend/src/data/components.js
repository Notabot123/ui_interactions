const groups = [
  ["Powertrain", ["Turbocharger Assembly", "Crankshaft", "Fuel Injector Rail", "Combustion Chamber", "Starter Motor"]],
  ["Hydraulics", ["Hydraulic Pump HP-204", "Servo Valve SV-18", "Pressure Regulator PR-9", "Accumulator Vessel", "Return Filter RF-22"]],
  ["Electrical", ["Control Module CM-71", "Sensor Harness", "Battery Isolator", "Relay Bank", "Telemetry Gateway"]],
  ["Cooling", ["Heat Exchanger HX-33", "Coolant Pump", "Radiator Matrix", "Thermostat Housing", "Expansion Tank"]],
  ["Structures", ["Main Bearing Housing", "Access Panel", "Mounting Bracket", "Inspection Hatch", "Composite Cowling"]],
  ["Pneumatics", ["Air Compressor", "Solenoid Manifold", "Dryer Cartridge", "Purge Valve", "Pressure Transducer"]]
]

function makeComponent(group, name, index) {
  const code = name.split(/\s+/).map(w => w[0]).join('').toUpperCase() + '-' + String(100 + index)
  return {
    id: `${group.toLowerCase()}-${index}`.replace(/[^a-z0-9-]/g, ''),
    group,
    name,
    code,
    status: index % 5 === 0 ? 'Attention required' : index % 3 === 0 ? 'Under inspection' : 'Operational',
    pressure: `${80 + (index * 7) % 65} PSI`,
    temperature: `${32 + (index * 3) % 48} °C`,
    description: `${name} is part of the ${group.toLowerCase()} subsystem. This placeholder represents a complex engineering model, drawing package, maintenance history and technical metadata.`,
  }
}

export const componentTree = groups.map(([group, names], gi) => ({
  group,
  items: Array.from({ length: 20 }, (_, i) => makeComponent(group, names[i % names.length], gi * 20 + i + 1))
}))

export const allComponents = componentTree.flatMap(g => g.items)
