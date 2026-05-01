# LuxAuth multi-sensor experiment plan: parts, circuits, and costs by phase

**Document version:** v1
**Date:** 2026-05-01
**Companion to:**
- [experiment-plan.md](experiment-plan.md) — the phased experiment plan whose phases this parts list operationalizes
- [MultiSensorAuthenticationApproach.md](../MultiSensorAuthenticationApproach.md) — strategic-options briefing at repo root
- [few-shot-academic-position.md](few-shot-academic-position.md) — academic-defense position for the system's few-shot operation

All prices in CAD, sourced where possible from Adafruit, Pi-Shop, Amazon Canada, and DigiKey Canada. Prices subject to change but reasonably current as of 2026. All ASCII diagrams use a fixed width and standard pin labeling conventions.

---

## Phase E0: Capacitive proof-of-concept

### Hardware list

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| Raspberry Pi 5 (16GB) | Already owned | $0 | Or any Pi you have on hand |
| FDC1004 breakout (Adafruit 5841) | Adafruit / Pi-Shop | $20 | I2C-based capacitance-to-digital converter |
| Copper foil tape, 50mm wide, 5m roll | Amazon | $15 | For DIY electrodes |
| Jumper wires, F/F and F/M, 40-pack | Pi-Shop | $8 | |
| Small breadboard | Pi-Shop | $7 | Half-size is fine |
| BME280 environmental sensor | Adafruit / Pi-Shop | $15 | Logs temperature and humidity during readings |
| Flat acrylic sheet 200x200mm | Hardware store | $10 | Mounting surface for electrodes |
| Small fixed-weight test object (200g hobby weight) | Amazon | $8 | Provides repeatable contact pressure |
| **Total** | | **$83** | |

Materials for testing (separate from hardware):
| Item | Source | Approx. cost (CAD) |
|---|---|---|
| Real leather scraps, three sources (vegetable-tanned, chrome-tanned, finished) | Tandy Leather / craft store | $30 |
| Synthetic leather samples | Fabric store | $15 |
| PVC sample | Fabric store | $5 |
| Coated canvas sample | Fabric store | $10 |
| Bonded leather sample | Craft store | $10 |
| **Total materials** | | **$70** |

**Phase E0 grand total: ~$153 CAD**

### Connector wiring

The FDC1004 is an I2C device. The Pi exposes I2C on GPIO pins 2 (SDA) and 3 (SCL).

```
Raspberry Pi 5                       FDC1004 Breakout
┌──────────────────┐                 ┌──────────────────┐
│                  │                 │                  │
│  Pin 1 (3.3V) ───┼─────────────────┤ VIN              │
│  Pin 6 (GND)  ───┼─────────────────┤ GND              │
│  Pin 3 (SDA)  ───┼─────────────────┤ SDA              │
│  Pin 5 (SCL)  ───┼─────────────────┤ SCL              │
│                  │                 │                  │
│                  │                 │ CIN1 ────────────┼──→ to Electrode A
│                  │                 │ CIN2 ────────────┼──→ to Electrode B (optional)
│                  │                 │ SHIELD ──────────┼──→ to Shield plane (optional)
│                  │                 │                  │
└──────────────────┘                 └──────────────────┘

BME280 (also I2C, on same bus, different address)
┌──────────────────┐
│                  │
│ VIN  ←────── from Pi 3.3V (shared)
│ GND  ←────── from Pi GND (shared)
│ SDA  ←────── from Pi SDA (shared)
│ SCL  ←────── from Pi SCL (shared)
│                  │
└──────────────────┘
```

I2C addresses to expect: FDC1004 at 0x50, BME280 at 0x76 or 0x77. Verify with `i2cdetect -y 1` after wiring.

### Electrode construction

The simplest workable electrode is a parallel-plate capacitor formed by two strips of copper foil mounted on the acrylic sheet. The material under test sits between or on top of the electrodes.

```
ASCII top view of electrode pad (single-electrode mode):

┌──────────────────────────────────────┐
│                                      │
│   ┌──────────────────────────────┐   │
│   │                              │   │
│   │   Copper foil electrode      │   │
│   │   (50mm × 50mm)              │   │
│   │   Connected to FDC1004 CIN1  │   │
│   │                              │   │
│   └──────────────────────────────┘   │
│                                      │
│   Acrylic substrate (200mm × 200mm)  │
│                                      │
└──────────────────────────────────────┘

Material under test sits flat on the electrode.
The fixed weight is placed on top of the material to
ensure repeatable contact pressure.
```

For two-electrode (differential) mode later, two foil strips with a fixed gap between them, with the material spanning both:

```
┌──────────────────────────────────────┐
│                                      │
│  ┌──────────┐         ┌──────────┐   │
│  │          │  GAP    │          │   │
│  │  Elec A  │  10mm   │  Elec B  │   │
│  │          │         │          │   │
│  └──────────┘         └──────────┘   │
│       │                    │         │
│       └─→ CIN1        ←────┘         │
│                       CIN2           │
│                                      │
└──────────────────────────────────────┘
```

For E0, single-electrode mode is sufficient.

---

## Phase E1: Imaging modality survey

### Hardware list (additions to E0)

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| Pi Camera Module 3 NoIR | Pi-Shop | $50 | NoIR variant for IR capability; standard module if skipping IR |
| Pi Camera ribbon cable, 300mm | Pi-Shop | $5 | Longer cable for flexible mounting |
| Camera mount/tripod arm | Amazon | $25 | Adjustable for repeatable positioning |
| Convoy S2+ flashlight with Nichia 365nm UV LED | AliExpress / specialty UV vendor | $90 | The hobbyist standard for true 365nm UV |
| 850nm IR illuminator LED ring or array | Amazon | $30 | For NoIR camera IR mode |
| Linear polarizer film, 200mm × 200mm | Edmund Optics / Amazon | $25 | Cut into camera and light source filters |
| Small light tent/photo box, 40cm | Amazon | $60 | Controlled visible-light environment |
| White LED panel for visible illumination | Amazon | $30 | Diffused source inside the tent |
| Adjustable goose-neck LED for raking light | Amazon | $25 | Single-source directional light |
| Calibration targets: | | | |
| - X-Rite ColorChecker Passport (used) | eBay | $80 | Visible color reference |
| - UV fluorescence reference card (DIY) | Forensic supply / DIY | $30 | Known fluorescent pigments on card |
| - IR reflectance reference (aluminum tape strips on board) | Hardware store | $10 | DIY IR standard |
| UV-blocking eye protection | Amazon | $20 | Required when UV source is operating |
| **E1 hardware additions** | | **$480** | |

**Cumulative through E1: ~$633 CAD** (E0 hardware $83 + E0 materials $70 + E1 additions $480)

### Connector wiring

The Pi Camera connects via the dedicated CSI ribbon cable connector on the Pi 5, not the GPIO. No GPIO additions for the camera itself.

The Convoy flashlight is battery-powered and operates standalone — it's not wired to the Pi. The operator switches it on/off as part of the capture sequence.

The IR illuminator depends on the specific product. Most ring-light style 850nm IR LEDs come with a USB power cable; plug into any USB power source (a Pi USB port works but consider a separate USB power supply to avoid loading the Pi):

```
Pi 5 USB-A or external USB power supply
          │
          ▼
  ┌───────────────┐
  │ IR illuminator│
  │ 850nm LED ring│
  │ (USB-powered) │
  └───────────────┘
```

If you want programmatic control over IR illumination (turning it on for IR captures, off otherwise), add a USB relay or a MOSFET-switched circuit driven from a Pi GPIO:

```
Pi GPIO 18 (or any free GPIO)
       │
       ▼
   ┌───────┐        VCC ─────┬───── IR LED ring (+)
   │ N-MOSFET     │
   │ IRLZ44N or   │
   │ similar      │
   │              │
   │ GATE ←───────┘
   │ DRAIN ───────────────── IR LED ring (−)
   │ SOURCE ←───── GND
   └───────┘
```

Add a 10kΩ pulldown on the gate, a 220Ω gate resistor, and a flyback diode if the load is inductive. For simple LED arrays the diode may not be needed.

The white LED panel and raking light are mains-powered devices in this phase, controlled by physical switches. Programmatic control of these isn't necessary at E1; the operator switches them as part of the sequence.

### Tent and lighting layout

```
Top-down view of capture station:

       ┌──────────────────────────────┐
       │       LIGHT TENT (40cm)      │
       │                              │
       │  ┌────────────────────────┐  │
       │  │                        │  │
       │  │  White LED panel       │  │
       │  │  (top, diffused)       │  │
       │  └─────────┬──────────────┘  │
       │            │                 │
       │            ▼                 │
       │  ┌──────────────────────┐    │
       │  │                      │    │
       │  │   Specimen position  │    │
       │  │   + calibration tgt  │    │
       │  │                      │    │
       │  └──────────────────────┘    │
       │            ▲                 │
       │            │ (camera looks   │
       │            │  down)          │
       │  ┌─────────┴────────────┐    │
       │  │ Pi Camera (mounted)  │    │
       │  └──────────────────────┘    │
       │                              │
       │ ◄── Raking light enters from │
       │     side at low angle        │
       │     (only when raking mode)  │
       │                              │
       │ ◄── UV flashlight from above │
       │     when UV mode (operator   │
       │     holds it; visible lights │
       │     off)                     │
       │                              │
       │ ◄── IR illuminator on        │
       │     adjustable arm, only     │
       │     when IR mode             │
       │                              │
       └──────────────────────────────┘
```

The polarizer film is cut into two pieces: one for the camera lens, one for the light source. Polarized capture has the operator orient the source polarizer at 0° and 90° relative to the lens polarizer for the two captures.

---

## Phase E2: Hyperspectral spot

### Hardware list (additions to E1)

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| SparkFun Triad Spectroscopy Sensor (AS7265x) | SparkFun via Pi-Shop or DigiKey | $95 | Three-chip 18-band sensor |
| Qwiic cable | Pi-Shop | $5 | If using Qwiic-compatible setup |
| Sensor positioning fixture (3D-printed or laser-cut) | DIY / Amazon | $20 | Holds sensor at fixed distance over specimen |
| **E2 hardware additions** | | **$120** | |

**Cumulative through E2: ~$753 CAD**

### Connector wiring

The Triad sensor uses I2C, sharing the bus with FDC1004 and BME280. It comes with three sensors at three I2C addresses (0x49, 0x4A, 0x4B):

```
Existing I2C bus on Pi 5 (Pin 3 SDA, Pin 5 SCL)
       │
       ├── FDC1004 (0x50) — already wired in E0
       ├── BME280 (0x76 or 0x77) — already wired in E0
       │
       └── SparkFun Triad
           ┌─────────────────────────┐
           │                         │
           │  3.3V ←─── from Pi 3.3V │
           │  GND  ←─── from Pi GND  │
           │  SDA  ←─── from Pi SDA  │
           │  SCL  ←─── from Pi SCL  │
           │                         │
           │  AS72651 (0x49)         │
           │  AS72652 (0x4A)         │
           │  AS72653 (0x4B)         │
           │                         │
           └─────────────────────────┘
```

The Triad's three onboard sensors share an I2C bus internally and present three separate addresses on the external bus. Each chip covers a different wavelength range (UV/visible, visible, NIR), and together they produce 18 bands.

Verify with `i2cdetect -y 1` after wiring; you should see four new addresses (the three Triad chips plus FDC1004 and BME280).

### Sensor positioning

The Triad is a single-spot sensor with an ~8mm field of view. Precise positioning matters for repeatability. A simple fixture:

```
Side view of Triad fixture over specimen:

              ┌──────────────────┐
              │ Triad PCB        │
              │ (sensor face     │
              │  pointing down)  │
              └────────┬─────────┘
                       │
                       │ Fixed standoff distance
                       │ (typically 5-10mm)
                       │
                ╔══════▼══════╗
                ║             ║
                ║  Specimen   ║
                ║             ║
                ╚═════════════╝
                  Reference
                  surface
```

The 3D-printed fixture holds the sensor at a fixed distance over a reference surface where the specimen is placed. The illumination for hyperspectral comes from the Triad's onboard white LED, so external lighting is irrelevant during hyperspectral capture (turn off other sources to avoid contamination).

---

## Phase E3: Thermal time-constant (passive)

### Hardware list (additions to E2)

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| MLX90614 IR thermometer (Adafruit 1747) | Adafruit / Pi-Shop | $35 | I2C non-contact IR temperature sensor |
| Insulated equilibration cabinet (small lunch cooler) | Amazon | $25 | Simple thermal-controlled environment |
| Small heating mat or seedling heat mat (low-power) | Amazon | $30 | Provides controlled warm environment in the cabinet |
| Adjustable thermostat (analog, for heat mat) | Amazon | $20 | Maintains stable equilibration temperature |
| Sensor positioning fixture for MLX90614 | DIY | $15 | Fixed distance over specimen |
| **E3 hardware additions** | | **$125** | |

**Cumulative through E3: ~$878 CAD**

### Connector wiring

The MLX90614 is also I2C, sharing the bus:

```
Existing I2C bus on Pi 5
       │
       ├── FDC1004 (0x50)
       ├── BME280 (0x76 or 0x77)
       ├── Triad chips (0x49, 0x4A, 0x4B)
       │
       └── MLX90614
           ┌─────────────────────────┐
           │                         │
           │  VIN ←─── from Pi 3.3V  │
           │  GND ←─── from Pi GND   │
           │  SDA ←─── from Pi SDA   │
           │  SCL ←─── from Pi SCL   │
           │                         │
           │  Default address: 0x5A  │
           │                         │
           └─────────────────────────┘
```

The MLX90614 reads ambient and object temperatures separately. For cooling-curve measurement, you sample object temperature periodically (e.g., every 100ms for 10-20 seconds) and record the curve.

The heating mat and thermostat are mains-powered and operate independently of the Pi. The mat warms the equilibration cabinet to a target temperature (e.g., 30°C if room is 22°C); samples sit in the cabinet for the equilibration period before measurement.

### Thermal capture geometry

```
Side view, equilibration phase:

  ┌──────────────────────────────┐
  │  Insulated cabinet           │
  │                              │
  │  ┌────────────────────────┐  │
  │  │ Heating mat (bottom)   │  │
  │  └────────────────────────┘  │
  │                              │
  │  Specimens placed on top of  │
  │  the mat, allowed to reach   │
  │  cabinet temperature         │
  │  (10-20 minutes)             │
  │                              │
  └──────────────────────────────┘

Side view, measurement phase:

  Specimen moved to cooler measurement
  area at room temperature.

  ┌─────────────────────┐
  │ MLX90614 sensor     │
  │ (mounted at fixed   │
  │  distance, ~30mm)   │
  └──────────┬──────────┘
             │
             │ IR field of view ~5° angle
             │
       ╔═════▼═════╗
       ║  Specimen ║
       ║  cooling  ║
       ╚═══════════╝

  Pi samples temperature every 100ms for 10-20s,
  producing a cooling curve.
```

---

## Phase E4: Magnetic and structured metadata

### Hardware list (additions to E3)

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| Hall effect sensor module (analog, A1324 or similar) | Adafruit / Amazon | $8 | Or use DRV5053 module |
| ADS1115 16-bit ADC (Adafruit 1085) | Adafruit / Pi-Shop | $20 | Pi has no native ADC; needed for analog Hall output |
| Hall sensor probe assembly (DIY: sensor + cable + plastic housing) | DIY | $15 | Hand-held probe for hardware regions |
| Digital scale, 0.1g resolution, 1kg capacity | Amazon | $35 | For item weight |
| Digital caliper, 150mm | Amazon | $25 | For dimensional measurements |
| **E4 hardware additions** | | **$103** | |

**Cumulative through E4: ~$981 CAD**

### Connector wiring

The Hall sensor is an analog device. The Pi has no analog inputs, so an ADC is required. The ADS1115 is I2C and shares the bus:

```
ADS1115 wiring:
       │
       ├── VIN ←─── from Pi 3.3V (or 5V; ADS1115 accepts both)
       ├── GND ←─── from Pi GND
       ├── SDA ←─── from Pi SDA (shared bus)
       ├── SCL ←─── from Pi SCL (shared bus)
       │
       │   I2C address 0x48 (default; configurable to 0x49, 0x4A, 0x4B)
       │
       │   Analog inputs:
       ├── A0 ←─── from Hall sensor signal output
       ├── A1, A2, A3 ←── unused (available for future analog sensors)

Hall sensor module wiring:
       │
       ├── VCC ←─── from Pi 3.3V
       ├── GND ←─── from Pi GND
       └── OUT ──→ to ADS1115 A0
```

I2C address summary at this point (E4):

```
0x48 — ADS1115
0x49 — Triad AS72651
0x4A — Triad AS72652
0x4B — Triad AS72653
0x50 — FDC1004
0x5A — MLX90614
0x76 (or 0x77) — BME280
```

No address conflicts. All seven devices coexist on the single I2C bus.

The digital scale and caliper are standalone tools; their readings are entered manually into the capture session metadata or, if you want automation, both have models with USB or Bluetooth output that integrate with the Pi via standard interfaces.

### Hall probe geometry

```
Side view of Hall sensor probe:

  Plastic handle
  ┌────────────────┐
  │                │
  │   ┌───┐        │
  │   │A0 │ ← Hall sensor chip
  │   │   │   at probe tip
  │   └───┘        │
  │     │          │
  │     │ 3-wire   │
  │     │ cable    │
  │     │          │
  └─────┼──────────┘
        │
        │ to ADS1115 A0 (signal)
        │ to Pi 3.3V (VCC)
        │ to Pi GND (GND)
        │
        ▼

  Operator places probe tip against metal hardware.
  Reading is recorded as the analog voltage from the
  Hall sensor, converted to magnetic field strength
  using the sensor's datasheet calibration.
```

---

## Phase E5: First real-item validation (integration phase)

No new sensors. This phase integrates everything from E0-E4 into a unified capture station and adds the device-side software stack and Pi-to-Mac networking.

### Hardware additions for integration

| Item | Source | Approx. cost (CAD) | Notes |
|---|---|---|---|
| Integration hub board (custom-cut prototype PCB or large breadboard) | Adafruit / Pi-Shop | $25 | Replaces the now-overcrowded breadboard |
| Cable management and connector kit | Amazon | $30 | XT60, JST, or screw-terminal connectors for clean wiring |
| Touchscreen for operator UI (Pi-compatible 7" HDMI touch) | Pi-Shop | $90 | Or use a phone via web UI for $0 |
| Lockable enclosure for the rig (large plastic case or built box) | Amazon / hardware store | $80 | Protects the breadboarded electronics |
| USB hub (powered, 4-port) | Amazon | $25 | Reduces load on Pi USB ports |
| Wi-Fi configured between Pi and Mac | $0 | $0 | Already exists |
| **E5 hardware additions** | | **$250** | |

**Cumulative through E5: ~$1231 CAD**

Item acquisition costs for testing (separate; highly variable):

| Item type | Approx. cost (CAD) |
|---|---|
| 2 known-authentic items (your own or borrowed) | $0 |
| 1 known-counterfeit item (cheap obvious fake) | $30-80 |
| 1 aged-authentic item (older bag, wallet, etc.) | $100-300 |
| **Item acquisition for E5** | **$130-380** |

### Final integrated wiring overview

```
Raspberry Pi 5
┌───────────────────────────────────────────────┐
│                                               │
│  CSI Camera ribbon ←──→ Pi Camera Module 3    │
│                          (NoIR variant)       │
│                                               │
│  GPIO Pin 1 (3.3V) ──→ I2C bus VCC            │
│  GPIO Pin 6 (GND)  ──→ I2C bus GND            │
│  GPIO Pin 3 (SDA)  ──→ I2C bus SDA            │
│  GPIO Pin 5 (SCL)  ──→ I2C bus SCL            │
│                                               │
│  GPIO Pin 12 (GPIO 18) ──→ MOSFET gate (IR)   │
│                                               │
│  USB-A ──→ Powered USB hub ──→ IR illuminator │
│                                               │
│  HDMI ──→ Touchscreen (operator UI)           │
│                                               │
│  Ethernet/WiFi ──→ Mac backend                │
│                                               │
└───────────────────────────────────────────────┘
                       │
                       ▼
        Shared I2C bus (single set of pull-ups
        on the Pi side, typically 1.8kΩ to 3.3V):

  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
  │ FDC1004 │ Triad   │ MLX90614│ ADS1115 │ BME280  │ ...     │
  │ 0x50    │ 0x49-4B │ 0x5A    │ 0x48    │ 0x76    │         │
  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘

  ADS1115 A0 ←── Hall effect sensor (analog, on probe)
  FDC1004 CIN1 ←── Capacitive electrode (on test surface)
```

### Electrical considerations at integration

**I2C pull-ups.** The Pi 5 has internal pull-ups on the I2C lines, but with seven devices on the bus the capacitance starts to matter. If you see communication errors at 400kHz, drop to 100kHz or add external 1.8-2.2kΩ pull-ups to 3.3V on SDA and SCL. Most breakout boards include their own pull-ups, which can compound; if so, remove the ones from all but the master breakout (typically the FDC1004's pull-ups can stay; remove from others if necessary by cutting solder jumpers, which is documented per board).

**Power budget.** The Pi 5 with all sensors active draws roughly 6-8W, well within the 27W official PSU rating. The IR illuminator is the largest separate load and should not be drawn from Pi USB if it pulls more than 500mA — use the powered hub or an external supply.

**Cable lengths.** Keep I2C cables short (under 30cm total bus length) to minimize signal integrity issues. The Hall probe cable can be longer (up to ~1m) since it carries an analog signal that's tolerated by the ADS1115's input filtering, but shielded cable is recommended.

**Calibration target storage.** All targets (ColorChecker, UV reference, IR reference, capacitive reference, thermal reference) live in a labeled box adjacent to the rig. Each capture session begins with a calibration captures pass before specimen captures.

---

## Phase E6: Expanded real-item validation

No new electrical hardware. This phase is about scale: more items, more captures, refinement of the operator workflow, and full per-modality calibration of K-curves and abstention thresholds.

### Item acquisition costs (the dominant E6 cost)

| Item type | Approx. cost (CAD) |
|---|---|
| 20-30 authentic items across 2-3 categories | $1000-5000 (variable; partnerships may reduce) |
| 5-10 counterfeit items including superfakes | $300-1500 (superfakes are not cheap) |
| **Item acquisition for E6** | **$1300-6500** |

### Possible hardware refinements during E6

If specific issues surface during E5 that warrant rebuilds:

| Possible refinement | Approx. cost (CAD) |
|---|---|
| Custom PCB for the hub board (replacing breadboard) | $50-150 (small batch) |
| Solenoid-actuated soft-tipped striker for acoustic experiments (if added) | $80 |
| Improved photogrammetry rig (turntable, structured light scanner) | $100-300 |
| Active thermal heating module (replaces passive equilibration) | $40 |
| **E6 refinements** | **$0-570 depending on choices** |

**Cumulative through E6 (lower bound, hardware only): ~$1231 CAD**
**Cumulative through E6 (with refinements): ~$1800 CAD**
**Cumulative through E6 (with item acquisition, mid-range): ~$5000-7000 CAD**

---

## Cumulative budget summary

| Phase | Hardware additions | Cumulative hardware | Item materials |
|---|---|---|---|
| E0 | $83 | $83 | $70 |
| E1 | $480 | $563 | $0 |
| E2 | $120 | $683 | $0 |
| E3 | $125 | $808 | $0 |
| E4 | $103 | $911 | $0 |
| E5 | $250 | $1161 | $130-380 |
| E6 | $0-570 | $1161-1731 | $1300-6500 |
| **Total program** | | **~$1200-1730** | **~$1500-6900** |

The hardware total runs $1200-1730 CAD across the full program. Item acquisition is the dominant variable cost and ranges from $1500 if you can borrow most items or use proxy materials creatively to over $6000 if you're sourcing superfakes for E6 specifically. Total program cost: $2700-8600 CAD depending on item access.

The hardware is heavily front-loaded (most of the rig is built by E5 at $1161). E6 is mostly time and item acquisition rather than hardware spend.

---

## A note on what's deliberately not in the parts list

A few things some sources would push you toward that aren't here, with reasons:

**A microscope or USB microscope.** This program is explicitly not microscopy. If you wanted to maintain a microscopy capability for comparison, that's a separate project with separate parts, not part of this experiment plan.

**A spectrometer beyond the Triad.** Real lab-grade spectrometers (Ocean Optics, Hamamatsu) start at $2000-5000 and aren't justified at this stage. If E2 reveals that the Triad's 18 bands aren't enough and finer spectral resolution would unlock something, revisit this in a phase after E6.

**A FLIR/Seek thermal camera.** Some reviewers suggested thermal imaging. The MLX90614 is a single-point sensor; a thermal camera would give spatial thermal information. Not in this plan because (a) cost is $200-300 for a phone-attachable thermal camera, (b) the science can be tested with the simpler MLX90614 first, and (c) if the simple version doesn't show signal, the more complex version probably won't either.

**An impedance analyzer beyond FDC1004.** The AD5933-based modules give you frequency-swept impedance spectroscopy, which is more discriminative than the FDC1004's single-frequency capacitance measurement. Worth considering for a phase after E6 if capacitive proves valuable and frequency-domain information would add discrimination. Not needed for E0's basic question of "does dielectric measurement distinguish materials."

**Any acoustic hardware.** Acoustic stays out of the experiment plan as previously discussed. If an acoustic phase is added later (E5b or post-E6), it would add maybe $80-150 in piezo sensors, solenoid striker, and signal conditioning.

That's the parts and circuits picture, phase by phase, with cumulative budget. Each phase is built incrementally on the previous, no big-bang integration. Each addition is testable on its own before becoming part of the integrated rig.
