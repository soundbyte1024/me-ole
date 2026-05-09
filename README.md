# ME-OLE — ME Offline Editor

Web-based GUI for creating and editing Allen & Heath ME-1 personal monitor mixer config files (`.ME1`).
Runs in Docker — works on Windows, Mac (Intel & Apple Silicon), Linux, and Raspberry Pi.

No Python. No pip. Nothing else required.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / Mac)
- Docker Engine (Linux / Raspberry Pi)

---

## Quick Start

1. Download `docker-compose.hub.yml` from this repository
2. Edit it and replace `YOUR_GITHUB_USERNAME` with `soundbyte1024`
3. Run:

```bash
docker compose -f docker-compose.hub.yml up -d
```

4. Open **http://localhost:5000** in your browser

To stop:
```bash
docker compose -f docker-compose.hub.yml down
```

To update to the latest version:
```bash
docker compose -f docker-compose.hub.yml pull
docker compose -f docker-compose.hub.yml up -d
```

Docker automatically pulls the correct image for your platform:

| Platform | Architecture |
|---|---|
| Windows PC / Linux x86 | `linux/amd64` |
| Mac (Apple Silicon M1/M2/M3) | `linux/arm64` |
| Raspberry Pi 4 / 5 | `linux/arm64` |
| Raspberry Pi 3 and older | `linux/arm/v7` |

---

## Using the Editor

### Loading a config

Click **Open** in the top bar and select a `.ME1` file exported from your ME-1.
To export from the device: insert a USB drive, go to **Utility → Save Config to USB**.

You can also click **New** to start a blank config from scratch.

### Presets

The preset list runs down the left side. Click a preset to select it.
Change the name in the text box next to the preset list.
Up to 16 presets are supported.

### Assigning buttons

Click any of the 16 channel buttons on the hardware image to open the button editor on the right.

Choose the assignment type using the pills at the top of the editor:

| Type | Description |
|------|-------------|
| **Single** | One input channel. Set the channel number, level, and pan. |
| **Group** | Multiple input channels mixed together. Select channels from the grid, set per-channel level and pan. |
| **Auto** | Auto Mode — the ME-1 assigns the channel automatically based on the console. |
| **Aux In** | Routes the auxiliary input to this button. |
| **1kHz Sine** | Test tone. |
| **Blank** | Clears the button assignment. |

### Groups

Switch to the **Group** type, then click channels in the channel grid to add them to the group.
Each selected channel gets its own level and pan controls in the table below.
Enter a label (up to 6 characters) or check **Use device default** to let the ME-1 name it automatically.

### EQ and Limiter

Click the **Master** button (top right of the hardware image) to open the EQ and Limiter panel.

- **Lo / Mid / Hi** gain sliders: ±12 dB shelving/peak bands
- **Mid Freq** dropdown: 16 frequency options from 200 Hz to 5 kHz
- **Limiter**: Off, or −3 dBFS to −27 dBFS in 3 dB steps
- The frequency response graph updates live as you adjust the sliders

Click **Apply EQ & Limiter** to save changes to the current preset.

### Saving

Change the config name with the yellow text box in the top bar. The name will be automatically formatted to ME-1 requirements.
Click **Save .ME1** to download the config file.
To load it onto the device: copy the file to a USB drive and use **Utility → Load Config from USB** on the ME-1.

Use **Saved Configs** to store and manage multiple configs within the app itself.

---

## Notes on device-exported files

The ME-1 firmware occasionally exports files with minor corruption in the button data — truncated labels (e.g. "Bass" saved as "ass"), missing channel assignments, or incorrect flag bytes. ME-OLE detects and corrects these automatically where possible. Buttons where the channel number was lost entirely are shown with a red indicator and prompt you to re-enter the channel number manually.

---

## Building from source

```bash
docker compose up --build -d
```

---

## Troubleshooting

**Port 5000 already in use**
Change `"5000:5000"` to `"5001:5000"` in the compose file, then open http://localhost:5001.

**Force a clean rebuild**
```bash
docker compose build --no-cache
```

**Raspberry Pi: wrong architecture pulled**
Ensure you are using Docker Engine 19.03 or later, which supports multi-platform image selection automatically.

---

## Compatibility

Tested against ME-1 firmware exported `.ME1` files with up to 16 presets.
ME-500 support is not yet implemented.

---

## Feedback and bugs

Please open an issue on GitHub if you encounter a problem or have a feature suggestion.
Including the `.ME1` file that caused the issue (if applicable) will help greatly with diagnosis.
